# Database Feature Contracts

The API endpoints below are already wired and expect database objects with these
names/signatures. The SQL that creates each object is written by the student;
this document only records **what** each object must accomplish so the
integration works. Until an object exists, its endpoint returns HTTP 501.

---

## Views (`sql/views.sql`)

### `v_projects`
- Consumed by: `GET /projects/`
- Purpose: return all projects with full columns
- Session vars: none
- API note: results returned as-is (`SELECT *`), ordered by `id`

### `v_overdue_tasks`
- Consumed by: `GET /reports/tasks/overdue`
- Purpose: rows for tasks whose deadline has passed and which are not
  finished/cancelled. Should expose enough context to be readable on its own
  (at minimum task identity plus its project/milestone context).
- Session vars: none
- API note: results returned as-is, ordered by `deadline`

### `v_assignee_workload`
- Consumed by: `GET /reports/workload`
- Purpose: one row per user who is assigned tasks, aggregating their current
  workload (e.g., how many open tasks they carry). Must include an
  `assignee_id` column; users with zero open tasks may or may not appear.
- Session vars: none
- Suggested columns: assignee_id, assignee_username, assignee_email, open_task_count, overdue_task_count
- API note: returned as-is

---

## Procedures (`sql/procedures.sql`)

### CREATE Operations (7)

#### `sp_create_user(p_username VARCHAR(50), p_email VARCHAR(150), p_password_hash VARCHAR(255), OUT p_user_id INT)`
- Consumed by: `POST /auth/register`
- Purpose: create a new user as an encapsulated database operation.
- Parameters: username, email, password hash; OUT parameter returns the new user ID.
- Error handling: duplicate username/email bubble up as MySQL errno 1062 → API returns 409.

#### `sp_create_project(p_name VARCHAR(150), p_description TEXT, p_start_date DATE, p_deadline DATE, p_status ENUM, OUT p_project_id INT)`
- Consumed by: `POST /projects/`
- Purpose: create a new project as an encapsulated database operation.
- Parameters: all project fields from ProjectCreate payload; OUT parameter returns the new project ID.
- Error handling: date constraint violation (deadline before start date) bubbles up as MySQL errno 3819 → API returns 400.

#### `sp_create_project_with_milestone(p_name VARCHAR(150), p_description TEXT, p_start_date DATE, p_deadline DATE, p_status ENUM, p_milestone_name VARCHAR(150), p_milestone_description TEXT, p_milestone_deadline DATE, p_milestone_status ENUM, OUT p_project_id INT, OUT p_milestone_id INT)`
- Consumed by: `POST /projects/with-milestone`
- Purpose: create a project **and** its first milestone atomically (transaction).
- Interaction: START TRANSACTION / COMMIT / ROLLBACK; if any step fails, nothing is persisted.
- Error handling: date constraint violation (errno 3819) → 400; FK violation (errno 1452) → 404.
- OUT parameters: project ID and milestone ID.

#### `sp_create_milestone(p_project_id INT, p_name VARCHAR(150), p_description TEXT, p_deadline DATE, p_status ENUM, OUT p_milestone_id INT)`
- Consumed by: `POST /milestones/`
- Purpose: create a new milestone as an encapsulated database operation.
- Parameters: project_id and all milestone fields; OUT parameter returns the new milestone ID.
- Error handling: foreign key violation (project not found) bubbles up as MySQL errno 1452 → API returns 404.

#### `sp_create_task(p_milestone_id INT, p_assignee_id INT, p_name VARCHAR(150), p_description TEXT, p_priority ENUM, p_deadline DATE, OUT p_task_id INT)`
- Consumed by: `POST /tasks/`
- Purpose: create a new task as an encapsulated database operation.
- Parameters: all task fields from TaskCreate payload; OUT parameter returns the new task ID.
- Error handling: foreign key violations (milestone/assignee not found) bubble up as MySQL errno 1452 → API returns 404.

#### `sp_update_task_status(p_task_id INT, p_new_status ENUM('TODO','IN_PROGRESS','COMPLETED','CANCELLED'), p_action VARCHAR(100))`
- Consumed by: `POST /tasks/{task_id}/start`, `POST /tasks/{task_id}/cancel`, `POST /tasks/{task_id}/complete`
- Purpose: update task status with business rule validation in a single database operation.
- Parameters: task ID, new status, action for logging.
- Business rules enforced:
  1. Task must exist (SIGNAL '45000' if not found)
  2. Task must not already be in the target status (SIGNAL '45000')
  3. Task must not be COMPLETED or CANCELLED (SIGNAL '45000' - terminal states)

#### `sp_complete_task(p_task_id INT)`
- Consumed by: `POST /tasks/{task_id}/complete`
- Purpose: mark a task as COMPLETED as an encapsulated database operation.
- Implementation: CALLs `sp_update_task_status(p_task_id, 'COMPLETED', 'complete')`.

### READ Operations (10)

#### `sp_get_user_by_id(p_user_id INT)`
- Consumed by: `GET /users/{user_id}`
- Returns: id, username, email, preferences, created_at
- Returns NULL if not found → API maps to 404

#### `sp_get_user_by_credentials(p_username_or_email VARCHAR(150))`
- Consumed by: `POST /auth/login`
- Returns: id, username, email, password_hash, preferences, created_at
- Searches by username OR email
- Returns NULL if not found → API maps to 401

#### `sp_get_project_by_id(p_project_id INT)`
- Consumed by: `GET /projects/{project_id}`
- Returns: all project columns
- Returns NULL if not found → API maps to 404

#### `sp_list_milestones(p_project_id INT)`
- Consumed by: `GET /milestones/` (optional query param project_id)
- If p_project_id is NULL: returns all milestones
- If p_project_id provided: filters by project_id
- Returns ordered by id

#### `sp_get_milestone_by_id(p_milestone_id INT)`
- Consumed by: `GET /milestones/{milestone_id}`
- Returns: all milestone columns
- Returns NULL if not found → API maps to 404

#### `sp_list_tasks(p_milestone_id INT, p_assignee_id INT, p_status VARCHAR(30))`
- Consumed by: `GET /tasks/` (optional query params)
- All parameters nullable; NULL means no filter
- Returns filtered tasks ordered by id

#### `sp_get_task_by_id(p_task_id INT)`
- Consumed by: `GET /tasks/{task_id}`
- Returns: all task columns
- Returns NULL if not found → API maps to 404

#### `sp_get_project_progress(p_project_id INT, OUT p_progress DECIMAL(5,2))`
- Consumed by: `GET /reports/projects/{project_id}/progress`
- Purpose: calculate project completion percentage.
- Returns: OUT parameter `p_progress` as DECIMAL(5,2) (0-100), or NULL if project has no tasks.
- Unknown project id: returns NULL → API maps to 404.
- Implementation: count tasks in project's milestones; compute completed/total * 100.

#### `sp_get_milestone_progress(p_milestone_id INT, OUT p_progress DECIMAL(5,2))`
- Consumed by: `GET /reports/milestones/{milestone_id}/progress`
- Purpose: calculate milestone completion percentage.
- Returns: OUT parameter `p_progress` as DECIMAL(5,2) (0-100), or NULL if milestone has no tasks.
- Unknown milestone id: returns NULL → API maps to 404.
- Implementation: count tasks in milestone; compute completed/total * 100.

### REPORT Operations (2) — Functions

#### `fn_get_project_progress(p_project_id INT)` RETURNS `DECIMAL(5,2)`
- Consumed by: `GET /reports/projects/{project_id}/progress`
- Purpose: calculate project completion percentage.
- Returns: `DECIMAL(5,2)` (0-100), or NULL if project has no tasks.
- Unknown project id: returns NULL → API maps to 404.
- Implementation: count tasks in project's milestones; compute completed/total * 100.

#### `fn_get_milestone_progress(p_milestone_id INT)` RETURNS `DECIMAL(5,2)`
- Consumed by: `GET /reports/milestones/{milestone_id}/progress`
- Purpose: calculate milestone completion percentage.
- Returns: `DECIMAL(5,2)` (0-100), or NULL if milestone has no tasks.
- Unknown milestone id: returns NULL → API maps to 404.
- Implementation: count tasks in milestone; compute completed/total * 100.

> **Note**: `GET /reports/tasks/overdue` and `GET /reports/workload` use views (`v_overdue_tasks`, `v_assignee_workload`) instead of stored procedures since they accept no parameters.

### UPDATE Operations (3) — Full UPDATE (all fields)

#### `sp_update_project(p_project_id INT, p_name VARCHAR(150), p_description TEXT, p_start_date DATE, p_deadline DATE, p_status ENUM)`
- Consumed by: `PUT /projects/{project_id}`
- Updates all project fields
- Error handling: date constraint violation (errno 3819) → 400
- Returns: affected rows; 0 → API maps to 404

#### `sp_update_milestone(p_milestone_id INT, p_name VARCHAR(150), p_description TEXT, p_deadline DATE, p_status ENUM)`
- Consumed by: `PUT /milestones/{milestone_id}`
- Updates all milestone fields
- Returns: affected rows; 0 → API maps to 404

#### `sp_update_task(p_task_id INT, p_milestone_id INT, p_assignee_id INT, p_name VARCHAR(150), p_description TEXT, p_priority ENUM, p_deadline DATE, p_status ENUM)`
- Consumed by: `PUT /tasks/{task_id}`
- Updates all task fields (full update)
- Error handling: FK violations (errno 1452) → 404
- Returns: affected rows; 0 → API maps to 404

### DELETE Operations (3) — Return Affected Rows

#### `sp_delete_project(p_project_id INT)`
- Consumed by: `DELETE /projects/{project_id}`
- Deletes project (cascades to milestones, tasks, activity_logs via FK)
- Returns: affected rows; 0 → API maps to 404

#### `sp_delete_milestone(p_milestone_id INT)`
- Consumed by: `DELETE /milestones/{milestone_id}`
- Deletes milestone (cascades to tasks, activity_logs via FK)
- Returns: affected rows; 0 → API maps to 404

#### `sp_delete_task(p_task_id INT)`
- Consumed by: `DELETE /tasks/{task_id}`
- Deletes task (cascades to activity_logs via FK)
- Returns: affected rows; 0 → API maps to 404

### USER Operations (1)

#### `sp_update_user_preferences(p_user_id INT, p_preferences JSON)`
- Consumed by: `PUT /users/{user_id}/preferences`
- Updates users.preferences column
- Returns: affected rows; 0 → API maps to 404

---

## Triggers (`sql/triggers.sql`)

### `trg_task_status_audit`
- Timing: AFTER UPDATE
- Table: `tasks`
- Action: whenever a row in `tasks` has its `status` changed, insert into
  `activity_logs` (`task_id`, `action`, `old_status`, `new_status`, `created_at`).
- Coverage: UPDATE only (INSERT doesn't change status; DELETE handled by FK cascade).
- Implementation:
  ```sql
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

---

## Transactions

### `sp_create_project_with_milestone` — **IMPLEMENTED**
- Atomically creates a project and its first milestone in a single transaction.
- Uses START TRANSACTION / COMMIT / ROLLBACK with an EXIT HANDLER for SQLEXCEPTION.
- Consumed by: `POST /projects/with-milestone`
- If any step fails (date constraint, FK violation, etc.), nothing is persisted.

---

## JSON (`users.preferences`, Sub-CPMK-6)

- Column: `users.preferences JSON NULL` (already in `schema.sql`).
- Wired endpoints:
  - `PUT /users/{user_id}/preferences` stores an arbitrary JSON object (whole-blob write).
  - `GET /users/{id}` returns it.
- Student work: demonstrate extraction/modification against this column using
  MySQL JSON functions during evaluation (e.g., reading a single preference
  key). Suggested demo data shape: `{"theme": "dark", "notifications": true}`.

---

## Indexes (`sql/indexes.sql`, Sub-CPMK-3/4)

No indexes beyond PKs/FKs exist yet — deliberately. Process:

1. Identify real query patterns (list endpoints filter by `assignee_id`,
   `status`, `milestone_id`; reports filter by deadline/status).
2. Inspect execution plans with EXPLAIN before adding anything.
3. Add only indexes justified by step 2, then re-run EXPLAIN and compare.
4. Document before/after observations in this folder.

Note: InnoDB automatically indexes foreign key columns and clusters data by
primary key; B+Tree is the implementation behind secondary indexes. Other
index types discussed in class (hash, bitmap, clustered/non-clustered) should
be related to theory vs. what MySQL actually provides here.