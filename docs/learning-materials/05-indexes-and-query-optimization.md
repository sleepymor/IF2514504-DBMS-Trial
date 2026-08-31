# Learning Material: Indexes & Query Optimization

---

## 1. Theory: How MySQL Indexes Work

### B+Tree Index Structure (InnoDB Default)

InnoDB uses **B+Tree** for all indexes:

```
                    [Root Page]
                       |
         +-------------+-------------+
         |                           |
    [Branch Page]              [Branch Page]
         |                           |
    +----+----+                 +----+----+
    |         |                 |         |
[Leaf]    [Leaf]            [Leaf]    [Leaf]
    |         |                 |         |
 (Data)    (Data)            (Data)    (Data)
```

**Key Properties:**
- **Balanced** — all leaf pages at same depth (typically 2–3 levels)
- **Sorted** — keys in ascending order within and across pages
- **Leaf pages contain data** — clustered index stores full row; secondary indexes store PK value

### Clustered vs. Secondary Indexes

| Property | **Clustered Index (PK)** | **Secondary Index** |
|---|---|---|
| **Data Location** | Leaf pages = full table rows | Leaf pages = (indexed columns + PK) |
| **Lookup Cost** | 1 B+Tree traversal | 2 traversals (secondary → PK → clustered) |
| **Storage** | Table itself | Separate B+Tree structures |
| **Auto-Created** | Yes (on PK or first UNIQUE NOT NULL) | Explicit `CREATE INDEX` |

> **InnoDB Rule:** Every table has exactly one clustered index. If no PK, InnoDB uses first `UNIQUE NOT NULL` column; otherwise generates hidden 6-byte `ROW_ID`.

---

## 2. Index Types in MySQL

| Type | Syntax | Use Case |
|---|---|---|
| **Primary Key** | `PRIMARY KEY (id)` | Row identity, clustered index |
| **Unique** | `UNIQUE KEY idx_email (email)` | Enforce uniqueness + fast lookup |
| **Secondary (B+Tree)** | `INDEX idx_status (status)` | Filtering, sorting, joining |
| **Composite** | `INDEX idx_milestone_status (milestone_id, status)` | Multi-column filters |
| **Fulltext** | `FULLTEXT idx_desc (description)` | Text search (not used here) |
| **Spatial** | `SPATIAL INDEX idx_loc (location)` | GIS data (not used here) |

---

## 3. Project Implementation: Index Catalog

**File:** `src/bismillah_mbd/sql/06-indexes.sql`

### 3.1 Single-Column Indexes

```sql
-- tasks table
CREATE INDEX idx_tasks_assignee_id ON tasks (assignee_id);
CREATE INDEX idx_tasks_milestone_id ON tasks (milestone_id);
CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_tasks_deadline ON tasks (deadline);

-- milestones table
CREATE INDEX idx_milestones_project_id ON milestones (project_id);
CREATE INDEX idx_milestones_status ON milestones (status);

-- projects table
CREATE INDEX idx_projects_status ON projects (status);

-- activity_logs table
CREATE INDEX idx_activity_logs_task_id ON activity_logs (task_id);
CREATE INDEX idx_activity_logs_created_at ON activity_logs (created_at);
```

### 3.2 Composite Indexes

```sql
-- Multi-column filters
CREATE INDEX idx_tasks_milestone_status ON tasks (milestone_id, status);
CREATE INDEX idx_tasks_assignee_status ON tasks (assignee_id, status);
CREATE INDEX idx_tasks_deadline_status ON tasks (deadline, status);
```

---

## 4. Query Patterns & Index Mapping

### Pattern 1: Filter by Assignee (`GET /tasks/?assignee_id=5`)

```sql
-- Procedure: sp_list_tasks
SELECT * FROM tasks
WHERE (p_milestone_id IS NULL OR milestone_id = p_milestone_id)
  AND (p_assignee_id IS NULL OR assignee_id = p_assignee_id)
  AND (p_status IS NULL OR status = p_status);
```

**Index:** `idx_tasks_assignee_id` or `idx_tasks_assignee_status`

---

### Pattern 2: Filter by Milestone (`GET /milestones/?project_id=3`)

```sql
-- Procedure: sp_list_milestones
SELECT * FROM milestones
WHERE p_project_id IS NULL OR project_id = p_project_id;
```

**Index:** `idx_milestones_project_id`

---

### Pattern 3: Overdue Tasks Report (`GET /reports/tasks/overdue`)

```sql
-- View: v_overdue_tasks
SELECT ... FROM tasks t
JOIN milestones m ON t.milestone_id = m.id
JOIN projects p ON m.project_id = p.id
WHERE t.deadline < CURDATE()
  AND t.status NOT IN ('COMPLETED', 'CANCELLED')
ORDER BY t.deadline;
```

**Indexes:** `idx_tasks_deadline_status` (deadline + status filter + ordering)

---

### Pattern 4: Workload Report (`GET /reports/workload`)

```sql
-- View: v_assignee_workload
SELECT u.id, u.username, u.email,
       COUNT(t.id) AS open_task_count,
       SUM(IF(t.deadline < CURDATE() AND ..., 1, 0)) AS overdue_task_count
FROM users u
JOIN tasks t ON u.id = t.assignee_id
WHERE t.status NOT IN ('COMPLETED', 'CANCELLED')
GROUP BY u.id, u.username, u.email;
```

**Indexes:** `idx_tasks_assignee_status` (assignee_id + status for join + filter)

---

### Pattern 5: Progress Functions

```sql
-- fn_get_project_progress
SELECT COUNT(*) FROM tasks t JOIN milestones m ON t.milestone_id = m.id
WHERE m.project_id = ?;
```

**Index:** `idx_tasks_milestone_id` (join) + `idx_milestones_project_id` (filter)

---

## 5. EXPLAIN Analysis: Reading Execution Plans

### Key Columns in `EXPLAIN`

| Column | Meaning | Good Values |
|---|---|---|
| `type` | Join/access type | `ref`, `range`, `eq_ref` (avoid `ALL`) |
| `possible_keys` | Indexes optimizer considered | Your index names |
| `key` | Index actually chosen | Your index name |
| `key_len` | Bytes of index used | Matches column sizes |
| `rows` | Estimated rows examined | Small number |
| `Extra` | Additional info | `Using index`, `Using where` |

### Example: Full Table Scan (Bad)

```sql
EXPLAIN SELECT * FROM tasks WHERE assignee_id = 5;
-- Before index:
-- type: ALL, key: NULL, rows: 10000, Extra: Using where
```

### Example: Index Range Scan (Good)

```sql
EXPLAIN SELECT * FROM tasks WHERE assignee_id = 5;
-- After idx_tasks_assignee_id:
-- type: ref, key: idx_tasks_assignee_id, rows: 5, Extra: Using where
```

### Example: Covering Index (Best)

```sql
EXPLAIN SELECT assignee_id, status FROM tasks WHERE assignee_id = 5;
-- type: ref, key: idx_tasks_assignee_status, rows: 5, Extra: Using index
-- "Using index" = all columns in index, no clustered lookup needed
```

---

## 6. Composite Index Design: Leftmost Prefix Rule

### Rule: Composite Index `(A, B, C)` Supports

| Query Pattern | Uses Index? |
|---|---|
| `WHERE A = 1` | ✅ |
| `WHERE A = 1 AND B = 2` | ✅ |
| `WHERE A = 1 AND B = 2 AND C = 3` | ✅ |
| `WHERE B = 2` | ❌ (not leftmost) |
| `WHERE B = 2 AND C = 3` | ❌ |
| `WHERE A = 1 AND C = 3` | ✅ (uses A only) |

### Project Composite Indexes Explained

```sql
-- idx_tasks_milestone_status (milestone_id, status)
-- Supports: milestone_id=X, milestone_id=X AND status='TODO'

-- idx_tasks_assignee_status (assignee_id, status)
-- Supports: assignee_id=X, assignee_id=X AND status='IN_PROGRESS'

-- idx_tasks_deadline_status (deadline, status)
-- Supports: deadline < CURDATE(), deadline < X AND status='TODO'
-- Also supports ORDER BY deadline (index is sorted)
```

---

## 7. Index Maintenance Cost

| Operation | Cost |
|---|---|
| `INSERT` | Write to clustered + all secondary indexes |
| `UPDATE` (indexed col) | Delete old + insert new in each index |
| `DELETE` | Remove from all indexes |
| Storage | ~10-30% of table size per index |

> **Only create indexes justified by actual query patterns.** Use `EXPLAIN` before and after.

---

## 8. Hands-On Exercises

### Exercise 1: Baseline Measurement
```sql
-- Disable query cache
SET SESSION query_cache_type = OFF;

-- Measure without indexes (drop them temporarily)
DROP INDEX idx_tasks_assignee_id ON tasks;
EXPLAIN ANALYZE SELECT * FROM tasks WHERE assignee_id = 5;
-- Note: rows examined, execution time
```

### Exercise 2: Add Index & Re-measure
```sql
CREATE INDEX idx_tasks_assignee_id ON tasks (assignee_id);
EXPLAIN ANALYZE SELECT * FROM tasks WHERE assignee_id = 5;
-- Compare: type, rows, execution time
```

### Exercise 3: Test Composite Index
```sql
EXPLAIN SELECT * FROM tasks WHERE milestone_id = 1 AND status = 'TODO';
EXPLAIN SELECT * FROM tasks WHERE milestone_id = 1;
EXPLAIN SELECT * FROM tasks WHERE status = 'TODO';  -- Won't use composite fully
```

### Exercise 4: Covering Index
```sql
-- Only indexed columns
EXPLAIN SELECT milestone_id, status FROM tasks WHERE milestone_id = 1;
-- Look for "Using index" in Extra
```

### Exercise 5: Index Statistics
```sql
SHOW INDEX FROM tasks;
ANALYZE TABLE tasks;  -- Updates cardinality stats
SELECT * FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'TaskManager' AND TABLE_NAME = 'tasks';
```

---

## 9. Architecture.md Load Order Rationale

```
1. 01-schema.sql      -- Tables, PKs (clustered indexes created)
2. 02-functions.sql   -- Scalar functions
3. 03-procedures.sql  -- Stored procedures
4. 04-triggers.sql    -- AFTER triggers (depend on tables)
5. 05-views.sql       -- Views (may reference functions)
6. 06-indexes.sql     -- Secondary indexes LAST
7. 07-seeder.sql      -- Optional test data
```

**Why indexes last?**
- Indexes slow down bulk data loading (seeder)
- Create after initial data load
- `ANALYZE TABLE` after index creation for optimizer stats

---

## 10. Summary Checklist

- [ ] InnoDB = B+Tree indexes; clustered = PK, secondary = separate trees
- [ ] Secondary index lookup = 2 traversals (index → PK → clustered)
- [ ] Composite index: leftmost prefix rule applies
- [ ] `EXPLAIN` columns: `type`, `key`, `rows`, `Extra`
- [ ] `Using index` = covering index (no clustered lookup)
- [ ] Indexes speed up reads, slow down writes — justify each
- [ ] Load order: schema → functions → procedures → triggers → views → indexes