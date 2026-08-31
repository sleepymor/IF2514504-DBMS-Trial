# Learning Material: Database Views

---

## 1. Theory: What Are Views?

A **VIEW** is a **virtual table** based on the result set of a `SELECT` statement. Unlike physical tables, views do not store data themselves; they store the *query definition*. Every time you query a view, the database executes the underlying query.

### Key Characteristics

| Property | Description |
|---|---|
| **Virtual** | No physical data storage; data comes from base tables at query time |
| **Updatable (sometimes)** | Simple views on a single table without aggregations can be updated; complex views are read-only |
| **Abstraction Layer** | Hide complexity (joins, filters, calculations) from applications |
| **Security** | Grant `SELECT` on a view without granting access to underlying tables |
| **Schema Stability** | Application queries stay valid even if base table structure changes |

### Syntax

```sql
CREATE [OR REPLACE] VIEW view_name [(column_list)] AS
SELECT column1, column2, ...
FROM table_name
[WHERE condition]
[ORDER BY column];
```

> **Best Practice:** Always list columns explicitly (`SELECT col1, col2...`) instead of `SELECT *`. This prevents breaking changes if underlying tables add/remove columns.

---

## 2. Views vs. Stored Procedures: When to Use Which?

| Aspect | **VIEW** | **Stored Procedure** |
|---|---|---|
| **Parameters** | None (uses session variables for filtering) | Explicit `IN` / `OUT` parameters |
| **Return Type** | Result set (table-like) | Result set, scalar values, or nothing |
| **Use Case** | Reusable *dataset* / *filterable collection* | *Operation* with business logic, transactions |
| **Composability** | Can be `JOIN`ed, `WHERE`d, nested in other views | Cannot be used in `FROM` clause of another query |
| **Performance** | Query optimizer merges view definition into outer query | Independent execution plan |

### Decision Rule for This Project

- **Use VIEW** when: The endpoint accepts **no parameters** (or only session variables) and returns a reusable dataset.
  - Examples: `GET /projects/`, `GET /reports/tasks/overdue`, `GET /reports/workload`

- **Use PROCEDURE** when: The endpoint **requires parameters** for filtering, or performs write operations / business logic.
  - Examples: `GET /projects/{id}`, `GET /tasks/?milestone_id=X`, `POST /tasks/`

---

## 3. Project Implementation: View Catalog

### 3.1 `v_projects` — All Projects Listing

**File:** `src/bismillah_mbd/sql/05-views.sql` (lines 6–16)  
**Consumed by:** `GET /projects/` → `routes/projects.py`

```sql
CREATE OR REPLACE VIEW v_projects AS
SELECT id,
       name,
       description,
       start_date,
       deadline,
       status,
       created_at,
       updated_at
FROM projects p
ORDER BY id;
```

**Learning Points:**
- Simple single-table view with explicit column list
- No `WHERE` clause — returns all rows
- `ORDER BY id` ensures consistent ordering for pagination
- No session variables needed (parameterless endpoint)

---

### 3.2 `v_overdue_tasks` — Overdue Tasks with Context

**File:** `src/bismillah_mbd/sql/05-views.sql` (lines 22–38)  
**Consumed by:** `GET /reports/tasks/overdue` → `routes/reports.py`

```sql
CREATE OR REPLACE VIEW v_overdue_tasks AS
SELECT t.id AS task_id,
       t.name AS task_name,
       t.status,
       t.deadline,
       t.priority,
       t.milestone_id,
       m.name AS milestone_name,
       m.project_id,
       p.name AS project_name,
       t.assignee_id
FROM tasks t
JOIN milestones m ON t.milestone_id = m.id
JOIN projects p ON m.project_id = p.id
WHERE t.deadline < CURDATE()
  AND t.status NOT IN ('COMPLETED', 'CANCELLED')
ORDER BY t.deadline;
```

**Learning Points:**
- **Multi-table join** (`tasks` → `milestones` → `projects`) for context
- **Business logic in `WHERE`**: deadline passed AND not terminal status
- **Column aliases** (`AS task_id`, `AS milestone_name`) for API-friendly names
- No parameters — static business rule ("overdue" = past deadline, not done)

---

### 3.3 `v_assignee_workload` — Aggregated Assignee Workload

**File:** `src/bismillah_mbd/sql/05-views.sql` (lines 45–56)  
**Consumed by:** `GET /reports/workload` → `routes/reports.py`

```sql
CREATE OR REPLACE VIEW v_assignee_workload AS
SELECT u.id AS assignee_id,
       u.username AS assignee_username,
       u.email AS assignee_email,
       COUNT(t.id) AS open_task_count,
       SUM(IF(t.deadline < CURDATE() AND t.status NOT IN ('COMPLETED', 'CANCELLED'), 1, 0))
           AS overdue_task_count
FROM users u
JOIN tasks t ON u.id = t.assignee_id
WHERE t.status NOT IN ('COMPLETED', 'CANCELLED')
GROUP BY u.id, u.username, u.email
HAVING open_task_count > 0
ORDER BY u.id;
```

**Learning Points:**
- **Aggregation** with `GROUP BY` + `COUNT()` / `SUM()`
- **Conditional aggregation** using `IF(condition, 1, 0)` inside `SUM()`
- **`HAVING` clause** filters groups (only assignees with open tasks)
- **`JOIN` filters out unassigned tasks** (INNER JOIN on `assignee_id`)

---

## 4. Parameterized Views Using Session Variables

MySQL views cannot accept parameters directly. The workaround: **session variables** (`@p_var`) set *before* the `SELECT`.

### Pattern (Not Used in This Project But Common)

```sql
-- View definition uses session variable
CREATE VIEW v_milestones AS
SELECT * FROM milestones
WHERE @p_project_id IS NULL OR project_id = @p_project_id;

-- Application sets variable, then queries
SET @p_project_id = 5;
SELECT * FROM v_milestones;
```

### Why This Project Uses Procedures Instead

The `dbm-features.md` specifies session variables for `v_milestones`, `v_tasks`, etc., but the Python implementation uses **stored procedures** for these endpoints because:

1. **Explicit parameters** are clearer in code (`cur.callproc("sp_list_tasks", (milestone_id, assignee_id, status))`)
2. **Type safety** — procedure parameters have declared types
3. **Easier debugging** — parameters visible in procedure signature

> **Session Variable Views** remain defined in `views.sql` for educational completeness, but the Python layer calls procedures for parameterized reads.

---

## 5. Python Integration: Calling Views

**File:** `src/bismillah_mbd/routes/projects.py` (line 147)  
**File:** `src/bismillah_mbd/routes/reports.py` (lines 56, 72)

```python
# Parameterless view — direct SELECT
cur.execute("""
    SELECT id, name, description, start_date, deadline, status, created_at, updated_at
    FROM v_projects
""")
return cur.fetchall()
```

**Key Rules:**
- **Never `SELECT *`** — list columns explicitly matching the view definition
- **Dictionary cursor** (`cursor(dictionary=True)`) returns `dict` rows matching Pydantic models
- **Error handling**: Catch `MySQLError` with `errno=1146` (table/view doesn't exist) → HTTP 501

---

## 6. Hands-On Exercises

### Exercise 1: Inspect View Definition
```sql
SHOW CREATE VIEW v_overdue_tasks;
```

### Exercise 2: Query View with Additional Filters
```sql
-- Add your own filter on top of the view
SELECT * FROM v_overdue_tasks
WHERE priority = 'URGENT'
  AND project_id = 1;
```

### Exercise 3: Execution Plan Comparison
```sql
EXPLAIN SELECT * FROM v_overdue_tasks;
EXPLAIN SELECT * FROM tasks t
JOIN milestones m ON t.milestone_id = m.id
JOIN projects p ON m.project_id = p.id
WHERE t.deadline < CURDATE() AND t.status NOT IN ('COMPLETED', 'CANCELLED');
```
> Observe: The optimizer merges the view into the outer query — plans are identical.

### Exercise 4: Create a New View
Create `v_active_projects_with_milestone_count`:
- Join `projects` + `milestones`
- Filter `projects.status = 'ACTIVE'`
- Count milestones per project
- Include project name, start_date, deadline, milestone_count

---

## 7. Summary Checklist

- [ ] Views = virtual tables, no data storage
- [ ] Use explicit column lists, never `SELECT *`
- [ ] Views for **parameterless reusable datasets**; Procedures for **parameterized operations**
- [ ] Session variable workaround exists but procedures preferred for typed parameters
- [ ] Python: explicit column list + dictionary cursor + proper error codes
- [ ] `EXPLAIN` shows view merging — no performance penalty