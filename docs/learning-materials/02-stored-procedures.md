# Learning Material: Stored Procedures & Transactions

---

## 1. Theory: What Are Stored Procedures?

A **stored procedure** is a precompiled collection of SQL statements and procedural logic (loops, conditionals, error handling) stored in the database server. Unlike views, procedures can:
- Accept **input parameters** (`IN`)
- Return **output parameters** (`OUT`, `INOUT`)
- Execute **transactions** with `COMMIT`/`ROLLBACK`
- Contain **business logic** (IF/ELSE, loops, SIGNAL)
- Return **multiple result sets**

### Syntax Overview

```sql
CREATE PROCEDURE procedure_name (
    IN  p_input_param   TYPE,
    OUT p_output_param  TYPE
)
[CHARACTERISTICS...]
BEGIN
    -- DECLARE variables
    -- SQL statements
    -- Control flow (IF, CASE, WHILE, LOOP)
    -- Exception handlers
END;
```

### Procedure Characteristics

| Characteristic | Purpose |
|---|---|
| `DETERMINISTIC` | Same inputs always produce same outputs (enables caching) |
| `READS SQL DATA` | Only reads data (no INSERT/UPDATE/DELETE) |
| `MODIFIES SQL DATA` | Performs writes (default if not specified) |
| `CONTAINS SQL` | Only SQL statements, no data access |
| `SQL SECURITY DEFINER` | Runs with creator's privileges (default) |
| `SQL SECURITY INVOKER` | Runs with caller's privileges |

---

## 2. Project Implementation: Procedure Catalog

### 2.1 CREATE Operations (7 Procedures)

#### `sp_create_user` — User Registration
```sql
CREATE PROCEDURE sp_create_user(
    IN p_username VARCHAR(50),
    IN p_email VARCHAR(150),
    IN p_password_hash VARCHAR(255),
    OUT p_user_id INT
)
BEGIN
    INSERT INTO users (username, email, password_hash)
    VALUES (p_username, p_email, p_password_hash);
    SET p_user_id = LAST_INSERT_ID();
END;
```
**Key Points:**
- `OUT` parameter returns auto-generated PK
- `IntegrityError` (errno 1062) on duplicate username/email → HTTP 409

---

#### `sp_create_project` — Project Creation
```sql
CREATE PROCEDURE sp_create_project(
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_start_date DATE,
    IN p_deadline DATE,
    IN p_status ENUM('PLANNED','ACTIVE','COMPLETED','CANCELLED'),
    OUT p_project_id INT
)
BEGIN
    INSERT INTO projects (name, description, start_date, deadline, status)
    VALUES (p_name, p_description, p_start_date, p_deadline, p_status);
    SET p_project_id = LAST_INSERT_ID();
END;
```
**Key Points:**
- `CHECK (deadline >= start_date)` constraint enforced by engine
- Violation → errno 3819 → HTTP 400

---

#### `sp_create_project_with_milestone` — **Atomic Transaction**
```sql
CREATE PROCEDURE sp_create_project_with_milestone(
    IN p_name VARCHAR(150), ..., OUT p_project_id INT, OUT p_milestone_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO projects ...; SET p_project_id = LAST_INSERT_ID();
    INSERT INTO milestones ...; SET p_milestone_id = LAST_INSERT_ID();
    COMMIT;
END;
```
**Key Points (Transaction Pattern):**
1. `DECLARE EXIT HANDLER FOR SQLEXCEPTION` — catches *any* SQL error
2. `ROLLBACK` — undoes all changes in transaction
3. `RESIGNAL` — re-throws original error to caller
4. `START TRANSACTION` / `COMMIT` — explicit boundaries
5. Two `OUT` parameters return both generated IDs

> **Why Transaction?** Creating a project + its first milestone must be atomic. If milestone insert fails, project must not exist.

---

#### `sp_create_milestone` / `sp_create_task`
Standard `INSERT` + `LAST_INSERT_ID()` pattern with FK validation:
- `sp_create_milestone`: FK `project_id` → errno 1452 → HTTP 404
- `sp_create_task`: FKs `milestone_id`, `assignee_id` → errno 1452 → HTTP 404

---

### 2.2 Business Rule Enforcement: `sp_update_task_status`

```sql
CREATE PROCEDURE sp_update_task_status(
    IN p_task_id INT,
    IN p_new_status ENUM('TODO','IN_PROGRESS','COMPLETED','CANCELLED'),
    IN p_action VARCHAR(100)
)
BEGIN
    DECLARE v_current_status VARCHAR(30);

    SELECT status INTO v_current_status FROM tasks WHERE id = p_task_id;
    IF v_current_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Task not found';
    END IF;

    IF v_current_status = p_new_status THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Task already in target status';
    END IF;

    IF v_current_status IN ('COMPLETED','CANCELLED') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot change status of terminal task';
    END IF;

    UPDATE tasks SET status = p_new_status WHERE id = p_task_id;
END;
```

**Key Points:**
- **`SIGNAL SQLSTATE '45000'`** — raises user-defined exception
- **Business rules in database** — cannot be bypassed by application
- **Three validations:**
  1. Task exists
  2. Not already in target status (idempotency)
  3. Not in terminal state (COMPLETED/CANCELLED are final)

---

### 2.3 Wrapper Procedure: `sp_complete_task`

```sql
CREATE PROCEDURE sp_complete_task(IN p_task_id INT)
BEGIN
    CALL sp_update_task_status(p_task_id, 'COMPLETED', 'complete');
END;
```
**Pattern:** Thin wrapper for semantic API endpoints (`POST /tasks/{id}/complete`).

---

### 2.4 READ Operations (Parameterized)

Procedures for parameterized reads (used instead of session-variable views):

```sql
-- Single entity by ID
CREATE PROCEDURE sp_get_project_by_id(IN p_project_id INT)
BEGIN
    SELECT id, name, description, start_date, deadline, status, created_at, updated_at
    FROM projects WHERE id = p_project_id;
END;

-- Filtered list with nullable parameters
CREATE PROCEDURE sp_list_tasks(
    IN p_milestone_id INT,
    IN p_assignee_id INT,
    IN p_status VARCHAR(30)
)
BEGIN
    SELECT ... FROM tasks
    WHERE (p_milestone_id IS NULL OR milestone_id = p_milestone_id)
      AND (p_assignee_id IS NULL OR assignee_id = p_assignee_id)
      AND (p_status IS NULL OR status = p_status)
    ORDER BY id;
END;
```

**Nullable Parameter Pattern:** `p_param IS NULL OR column = p_param` — allows optional filtering.

---

### 2.5 UPDATE / DELETE Operations

Full-update procedures (all columns) returning affected rows:
```sql
CREATE PROCEDURE sp_update_task(
    IN p_task_id INT, IN p_milestone_id INT, IN p_assignee_id INT,
    IN p_name VARCHAR(150), IN p_description TEXT, IN p_priority ENUM(...),
    IN p_deadline DATE, IN p_status ENUM(...)
)
BEGIN
    UPDATE tasks SET ... WHERE id = p_task_id;
END;
```
- Returns affected rows (0 → HTTP 404 in Python layer)
- FK violations (errno 1452) → HTTP 404

---

## 3. Python Integration: Calling Procedures

**File:** `src/bismillah_mbd/routes/*.py`

```python
with conn.cursor() as cur:
    cur.callproc("sp_create_project", (name, desc, start, deadline, status))
    for result in cur.stored_results():
        row = result.fetchone()
        if row:
            new_id = row[0]
            break
    else:
        new_id = cur.lastrowid
conn.commit()
```

**Key Patterns:**
| Pattern | Purpose |
|---|---|
| `cur.callproc(name, args)` | Execute procedure with positional params |
| `cur.stored_results()` | Iterator over result sets (SELECTs inside proc) |
| `cur.lastrowid` | Fallback for `OUT` param if not returned via result set |
| `conn.commit()` | Required after write procedures |
| `except IntegrityError` | Catch FK/UNIQUE violations → HTTP 409/404 |

**Error Mapping:**
| MySQL Errno | Cause | HTTP Status |
|---|---|---|
| 1062 | Duplicate UNIQUE (username/email) | 409 Conflict |
| 1452 | FK violation (not found) | 404 Not Found |
| 3819 | CHECK constraint (deadline < start) | 400 Bad Request |
| 1305 | Procedure not found | 501 Not Implemented |
| 45000 | SIGNAL (business rule) | 400/409 (app maps) |

---

## 4. Hands-On Exercises

### Exercise 1: Create a Procedure with Transaction
Create `sp_reassign_task(task_id, new_assignee_id)` that:
1. Verifies task exists
2. Verifies new assignee exists
3. Updates `assignee_id` in transaction
4. Returns new assignee info

### Exercise 2: Test Rollback
```sql
-- This should fail and rollback (deadline before start)
CALL sp_create_project('Bad', 'Test', '2025-01-10', '2025-01-01', 'PLANNED', @id);
SELECT @id; -- Should be NULL
```

### Exercise 3: Signal Handling
```sql
-- Trigger business rule error
CALL sp_update_task_status(999, 'COMPLETED', 'test');
-- Observe: ERROR 45000: Task not found
```

### Exercise 4: Procedure Introspection
```sql
SHOW CREATE PROCEDURE sp_create_project_with_milestone;
SHOW PROCEDURE STATUS WHERE Db = 'TaskManager';
SELECT * FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = 'TaskManager';
```

---

## 5. Summary Checklist

- [ ] Procedures = parameterized operations with business logic
- [ ] `IN`/`OUT` parameters for data exchange
- [ ] Transactions: `START TRANSACTION` + `COMMIT`/`ROLLBACK` + `EXIT HANDLER`
- [ ] `SIGNAL SQLSTATE '45000'` for business rule enforcement
- [ ] Nullable parameter pattern: `p_param IS NULL OR col = p_param`
- [ ] Python: `callproc()` + `stored_results()` + explicit commit
- [ ] Error mapping: MySQL errno → HTTP status codes