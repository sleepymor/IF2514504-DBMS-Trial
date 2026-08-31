# Learning Material: Database Triggers

---

## 1. Theory: What Are Triggers?

A **trigger** is a stored program that automatically executes ("fires") in response to specific **events** on a table. Triggers are part of the **active database** paradigm — the database reacts to changes without application intervention.

### Trigger Timing

| Timing | When It Fires | Typical Use Cases |
|---|---|---|
| `BEFORE` | Before the row is modified | Validate/modify input values, compute derived columns |
| `AFTER` | After the row is modified | Audit logging, cascade updates, notifications |

### Trigger Events

| Event | Fires On |
|---|---|
| `INSERT` | New row added |
| `UPDATE` | Existing row modified |
| `DELETE` | Row removed |

### Trigger Granularity

| Granularity | Fires |
|---|---|
| `FOR EACH ROW` | Once per affected row (most common) |
| `FOR EACH STATEMENT` | Once per SQL statement (not supported in MySQL) |

### Pseudo-Records: `OLD` and `NEW`

| Pseudo-Record | Available In | Contains |
|---|---|---|
| `NEW` | `INSERT`, `UPDATE` | New column values being written |
| `OLD` | `UPDATE`, `DELETE` | Old column values before change |

> **MySQL Limitation:** Only `FOR EACH ROW` supported. No statement-level triggers.

---

## 2. Syntax

```sql
CREATE TRIGGER trigger_name
{BEFORE | AFTER} {INSERT | UPDATE | DELETE}
ON table_name
FOR EACH ROW
[FOLLOWS | PRECEDES other_trigger]  -- MySQL 8.0+ ordering
BEGIN
    -- Trigger body
    -- Access columns via OLD.column, NEW.column
    -- Can use IF, SIGNAL, INSERT, UPDATE, etc.
END;
```

### Important Rules

1. **No transaction control** — cannot `COMMIT`/`ROLLBACK` inside trigger
2. **No `RETURN`** — triggers don't return values
3. **`SIGNAL` allowed** — can abort operation in `BEFORE` triggers
4. **Old/New are read-only in AFTER** — cannot modify `NEW` in `AFTER` triggers

---

## 3. Project Implementation: `trg_task_status_audit`

**File:** `src/bismillah_mbd/sql/04-triggers.sql`

```sql
DROP TRIGGER IF EXISTS trg_task_status_audit;

CREATE TRIGGER trg_task_status_audit
AFTER UPDATE ON tasks
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO activity_logs (task_id, action, old_status, new_status)
        VALUES (NEW.id, 'status_change', OLD.status, NEW.status);
    END IF;
END;
```

### Breakdown

| Component | Purpose |
|---|---|
| `AFTER UPDATE` | Fires after task row is successfully updated |
| `FOR EACH ROW` | Once per updated task |
| `IF OLD.status <> NEW.status` | Only log when status *actually changes* |
| `NEW.id` | PK of updated task (same as `OLD.id`) |
| `'status_change'` | Action type for filtering/querying |
| `OLD.status` → `NEW.status` | Transition captured for audit trail |

### Why `AFTER` Not `BEFORE`?

- `BEFORE` would fire even if UPDATE later fails (FK violation, etc.)
- `AFTER` guarantees the status change was **committed**
- Audit log should reflect *actual* state changes, not attempted ones

---

## 4. Trigger Coverage Analysis

### What This Trigger Covers ✅

| Operation | Triggered? | Reason |
|---|---|---|
| `UPDATE tasks SET status='IN_PROGRESS' WHERE id=1` | ✅ | Status changed |
| `UPDATE tasks SET status='COMPLETED' WHERE id=1` | ✅ | Status changed |
| `UPDATE tasks SET name='New Name' WHERE id=1` | ❌ | Status unchanged |
| `INSERT INTO tasks ...` | ❌ | No status *change* (initial status set) |
| `DELETE FROM tasks WHERE id=1` | ❌ | Handled by FK `ON DELETE CASCADE` |

### What Application Code Calls

| Endpoint | Procedure Called | Triggers Audit? |
|---|---|---|
| `POST /tasks/{id}/start` | `sp_update_task_status(id, 'IN_PROGRESS', 'start')` | ✅ |
| `POST /tasks/{id}/complete` | `sp_complete_task(id)` → `sp_update_task_status(..., 'COMPLETED', 'complete')` | ✅ |
| `POST /tasks/{id}/cancel` | `sp_update_task_status(id, 'CANCELLED', 'cancel')` | ✅ |
| `PUT /tasks/{id}` (full update) | `sp_update_task(..., status='IN_PROGRESS')` | ✅ if status changes |

---

## 5. Python Integration: Indirect via Procedures

**The Python layer never calls the trigger directly.** It calls procedures that modify data, and the trigger fires automatically.

```python
# routes/tasks.py
@router.post("/{task_id}/complete")
def complete_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    # ... fetch task ...
    with conn.cursor() as cur:
        cur.callproc("sp_complete_task", (task_id,))
    conn.commit()  # Trigger fires during this commit
    return fetch_task(conn, task_id)
```

**Key Insight:** The audit trail is **transparent to the application**. The application only needs to call the procedure; the database handles auditing.

---

## 6. Querying the Audit Trail

```sql
-- All status changes for a task
SELECT action, old_status, new_status, created_at
FROM activity_logs
WHERE task_id = 1
ORDER BY created_at;

-- Count status changes per task
SELECT task_id, COUNT(*) AS changes
FROM activity_logs
GROUP BY task_id;

-- Recent activity across all tasks
SELECT t.name AS task, al.action, al.old_status, al.new_status, al.created_at
FROM activity_logs al
JOIN tasks t ON al.task_id = t.id
ORDER BY al.created_at DESC
LIMIT 20;
```

---

## 7. Advanced Trigger Patterns

### 7.1 BEFORE Trigger for Validation

```sql
CREATE TRIGGER trg_validate_task_deadline
BEFORE INSERT ON tasks
FOR EACH ROW
BEGIN
    IF NEW.deadline < (SELECT start_date FROM milestones WHERE id = NEW.milestone_id) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Task deadline cannot be before milestone start date';
    END IF;
END;
```

### 7.2 BEFORE Trigger for Auto-Computation

```sql
CREATE TRIGGER trg_set_task_defaults
BEFORE INSERT ON tasks
FOR EACH ROW
BEGIN
    IF NEW.priority IS NULL THEN SET NEW.priority = 'LOW'; END IF;
    IF NEW.status IS NULL THEN SET NEW.status = 'TODO'; END IF;
END;
```

### 7.3 Multiple Triggers Same Event (MySQL 8.0+)

```sql
CREATE TRIGGER trg_audit_status AFTER UPDATE ON tasks FOR EACH ROW
FOLLOWS trg_task_status_audit  -- ensures order
BEGIN
    -- additional logging
END;
```

---

## 8. Hands-On Exercises

### Exercise 1: Test the Trigger
```sql
-- Setup
INSERT INTO users (username, email, password_hash) VALUES ('test', 't@t.com', 'hash');
INSERT INTO projects (name, start_date, deadline, status) VALUES ('P1', '2024-01-01', '2024-12-31', 'ACTIVE');
INSERT INTO milestones (project_id, name, deadline, status) VALUES (1, 'M1', '2024-06-30', 'PENDING');
INSERT INTO tasks (milestone_id, name, deadline, priority) VALUES (1, 'Task 1', '2024-05-01', 'HIGH');

-- Trigger fires
UPDATE tasks SET status = 'IN_PROGRESS' WHERE id = 1;

-- Verify
SELECT * FROM activity_logs WHERE task_id = 1;
```

### Exercise 2: Test No-Op Case
```sql
-- Update non-status column
UPDATE tasks SET name = 'New Name' WHERE id = 1;
SELECT * FROM activity_logs WHERE task_id = 1; -- Should NOT have new entry
```

### Exercise 3: Test via Procedure
```sql
CALL sp_update_task_status(1, 'COMPLETED', 'complete');
SELECT * FROM activity_logs WHERE task_id = 1;
```

### Exercise 4: Create a New Trigger
Create `trg_task_priority_escalation`:
- `BEFORE UPDATE` on `tasks`
- If `deadline < CURDATE() + INTERVAL 1 DAY` AND `priority <> 'URGENT'`
- Auto-set `NEW.priority = 'URGENT'`

### Exercise 5: Inspect Trigger Metadata
```sql
SHOW CREATE TRIGGER trg_task_status_audit;
SELECT * FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = 'TaskManager';
```

---

## 8. Summary Checklist

- [ ] Triggers = automatic reaction to DML events (INSERT/UPDATE/DELETE)
- [ ] `AFTER` for auditing (guarantees change committed); `BEFORE` for validation/modification
- [ ] `FOR EACH ROW` — only granularity in MySQL
- [ ] `OLD` (before) and `NEW` (after) pseudo-records
- [ ] Use `IF OLD.col <> NEW.col` to filter meaningful changes
- [ ] No transaction control, no `RETURN` inside triggers
- [ ] Application calls procedures; triggers fire transparently
- [ ] `activity_logs` provides immutable audit trail for compliance/debugging