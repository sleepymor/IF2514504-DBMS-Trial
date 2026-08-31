# Learning Material: Stored Functions

---

## 1. Theory: Functions vs. Procedures

| Aspect | **Stored Function** | **Stored Procedure** |
|---|---|---|
| **Return Value** | Single scalar value (`RETURN`) | None, or multiple result sets |
| **Parameters** | `IN` only (no `OUT`/`INOUT`) | `IN`, `OUT`, `INOUT` |
| **Usage in SQL** | Inside `SELECT`, `WHERE`, `HAVING`, `ORDER BY` | `CALL` statement only |
| **Transactions** | Cannot manage transactions | Can `START TRANSACTION`, `COMMIT`, `ROLLBACK` |
| **Side Effects** | Should be read-only (`READS SQL DATA`) | Can modify data (`MODIFIES SQL DATA`) |
| **Determinism** | `DETERMINISTIC` / `NOT DETERMINISTIC` | Not applicable |

> **Rule of Thumb:** Use a **function** when you need to compute a single value that can be used inline in a query. Use a **procedure** for operations, transactions, or multi-row results.

### Function Syntax

```sql
CREATE FUNCTION function_name (
    p_param1 TYPE,
    p_param2 TYPE
)
RETURNS RETURN_TYPE
[DETERMINISTIC | NOT DETERMINISTIC]
[READS SQL DATA | MODIFIES SQL DATA | CONTAINS SQL | NO SQL]
[SQL SECURITY {DEFINER | INVOKER}]
BEGIN
    DECLARE var_name TYPE;
    -- logic
    RETURN computed_value;
END;
```

### Key Characteristics

| Characteristic | Meaning |
|---|---|
| `DETERMINISTIC` | Same inputs → same output; enables query cache optimization |
| `NOT DETERMINISTIC` | Output may vary (e.g., uses `NOW()`, `RAND()`); default |
| `READS SQL Data` | Only `SELECT` statements; no writes |
| `MODIFIES SQL DATA` | Contains `INSERT`/`UPDATE`/`DELETE` (rare for functions) |
| `RETURNS NULL ON NULL INPUT` | Shortcut: if any arg is NULL, return NULL immediately |

---

## 2. Project Implementation: Scalar Functions

### 2.1 `fn_get_project_progress`

**File:** `src/bismillah_mbd/sql/02-functions.sql` (lines 6–30)

```sql
CREATE FUNCTION fn_get_project_progress(p_project_id INT)
RETURNS DECIMAL(5,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_total INT DEFAULT 0;
    DECLARE v_completed INT DEFAULT 0;

    SELECT COUNT(*) INTO v_total
    FROM tasks t
    JOIN milestones m ON t.milestone_id = m.id
    WHERE m.project_id = p_project_id;

    IF v_total = 0 THEN
        RETURN NULL;
    END IF;

    SELECT COUNT(*) INTO v_completed
    FROM tasks t
    JOIN milestones m ON t.milestone_id = m.id
    WHERE m.project_id = p_project_id AND t.status = 'COMPLETED';

    RETURN ROUND((v_completed / v_total) * 100, 2);
END;
```

**Learning Points:**
- **Returns** `DECIMAL(5,2)` — percentage with 2 decimal places (0.00–100.00)
- **`READS SQL DATA`** — declares read-only intent (optimizer can cache)
- **`DETERMINISTIC`** — same project_id always yields same progress
- **NULL handling** — returns `NULL` if project has no tasks (not 0%)
- **Two-phase aggregation** — count total, then count completed

---

### 2.2 `fn_get_milestone_progress`

**File:** `src/bismillah_mbd/sql/02-functions.sql` (lines 33–56)

```sql
CREATE FUNCTION fn_get_milestone_progress(p_milestone_id INT)
RETURNS DECIMAL(5,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_total INT DEFAULT 0;
    DECLARE v_completed INT DEFAULT 0;

    SELECT COUNT(*) INTO v_total FROM tasks WHERE milestone_id = p_milestone_id;

    IF v_total = 0 THEN
        RETURN NULL;
    END IF;

    SELECT COUNT(*) INTO v_completed
    FROM tasks
    WHERE milestone_id = p_milestone_id AND status = 'COMPLETED';

    RETURN ROUND((v_completed / v_total) * 100, 2);
END;
```

**Difference from Project Progress:**
- Single-table query (no join needed)
- Filters directly on `tasks.milestone_id`

---

## 3. Python Integration: Calling Functions

**File:** `src/bismillah_mbd/routes/reports.py` (lines 18–49)

```python
@router.get("/projects/{project_id}/progress")
def project_progress(project_id: int, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT fn_get_project_progress(%s)", (project_id,))
            row = cur.fetchone()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(status_code=501, detail="Function not found...")
        raise
    if row is None or row[0] is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "progress_percentage": row[0]}
```

**Key Differences from Procedure Calls:**
| Procedure (`callproc`) | Function (`execute`) |
|---|---|
| `cur.callproc("sp_name", (args,))` | `cur.execute("SELECT fn_name(%s)", (args,))` |
| `cur.stored_results()` → iterate | `cur.fetchone()` → direct scalar |
| `OUT` params in result set | Return value in first column |

---

## 4. Why Functions Here? (Design Decision)

### Could Have Been Procedures with OUT Parameters

```sql
-- Alternative: Procedure version
CREATE PROCEDURE sp_get_project_progress(
    IN p_project_id INT,
    OUT p_progress DECIMAL(5,2)
)
BEGIN
    -- same logic, SET p_progress = ...
END;
```

### Why Functions Won

1. **Composability** — `SELECT fn_get_project_progress(p.id) FROM projects p` works
2. **Direct Use in Queries** — `WHERE fn_get_project_progress(id) > 50`
3. **Cleaner Python** — single `execute()` + `fetchone()` vs `callproc()` + loop
4. **Semantic Fit** — "compute a value" not "perform an operation"
5. **Optimizer Hints** — `DETERMINISTIC` + `READS SQL DATA` enable caching

> **Architecture Rule (from `architecture.md`):** "Where a business rule or calculation belongs to the database, the API calls the database object (view / function / procedure) instead of reimplementing the logic in Python."

---

## 5. Advanced Function Patterns

### 5.1 Table-Valued Functions (MySQL 8.0+)

MySQL doesn't have true table-valued functions, but you can simulate with:
```sql
-- Not used here, but possible:
CREATE FUNCTION fn_get_user_tasks(p_user_id INT)
RETURNS JSON
READS SQL DATA
BEGIN
    RETURN (SELECT JSON_ARRAYAGG(JSON_OBJECT(...)) FROM tasks WHERE assignee_id = p_user_id);
END;
```

### 5.2 Functions in Generated Columns

```sql
-- Virtual generated column using function
ALTER TABLE projects
ADD COLUMN progress_pct DECIMAL(5,2)
GENERATED ALWAYS AS (fn_get_project_progress(id)) VIRTUAL;
```

### 5.3 Function in CHECK Constraint (MySQL 8.0.16+)

```sql
-- Enforce minimum progress before marking complete
ALTER TABLE projects
ADD CONSTRAINT chk_progress_before_complete
CHECK (status <> 'COMPLETED' OR fn_get_project_progress(id) = 100.00);
```

---

## 6. Hands-On Exercises

### Exercise 1: Test Function Directly
```sql
SELECT fn_get_project_progress(1) AS progress;
SELECT fn_get_milestone_progress(1) AS progress;
```

### Exercise 2: Use Function in Complex Query
```sql
-- Projects with progress > 50%
SELECT p.name, fn_get_project_progress(p.id) AS progress
FROM projects p
WHERE fn_get_project_progress(p.id) > 50;
```

### Exercise 3: Compare Procedure vs Function Call
```sql
-- Procedure
CALL sp_get_project_progress(1, @p);
SELECT @p;

-- Function
SELECT fn_get_project_progress(1);
```

### Exercise 4: Create a New Function
Create `fn_is_task_overdue(task_id)` returning `BOOLEAN`:
- Returns TRUE if deadline < CURDATE() AND status NOT IN ('COMPLETED','CANCELLED')
- Use in: `SELECT * FROM tasks WHERE fn_is_task_overdue(id)`

### Exercise 5: Inspect Function Metadata
```sql
SHOW CREATE FUNCTION fn_get_project_progress;
SELECT * FROM information_schema.ROUTINES
WHERE ROUTINE_TYPE = 'FUNCTION' AND ROUTINE_SCHEMA = 'TaskManager';
```

---

## 7. Summary Checklist

- [ ] Functions return **single scalar value** via `RETURN`
- [ ] Used **inline in queries** (`SELECT fn(...)`), not `CALL`
- [ ] `IN` parameters only; no `OUT`/`INOUT`
- [ ] Declare `READS SQL DATA` + `DETERMINISTIC` for read-only calculations
- [ ] Return `NULL` for "no data" (not 0) to distinguish "0%" from "N/A"
- [ ] Python: `execute("SELECT fn(%s)", (arg,))` + `fetchone()[0]`
- [ ] Prefer functions for **calculations**; procedures for **operations**