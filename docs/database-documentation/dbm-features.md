# Database Feature Contracts

The API endpoints below are already wired and expect database objects with these
names/signatures. The SQL that creates each object is written by the student;
this document only records **what** each object must accomplish so the
integration works. Until an object exists, its endpoint returns HTTP 501.

## Views (`sql/views.sql`)

### `v_overdue_tasks`
- Consumed by: `GET /reports/tasks/overdue`
- Purpose: rows for tasks whose deadline has passed and which are not
  finished/cancelled. Should expose enough context to be readable on its own
  (at minimum task identity plus its project/milestone context).
- API note: results are returned as-is (`SELECT *`), ordered by `deadline`.

### `v_assignee_workload`
- Consumed by: `GET /reports/workload`
- Purpose: one row per user who is assigned tasks, aggregating their current
  workload (e.g., how many open tasks they carry). Must include an
  `assignee_id` column; users with zero open tasks may or may not appear,
  student's design decision (document it).
- API note: returned as-is.

Suggested additional views (not wired yet, optional):
- `v_project_progress`, `v_task_status_report`.

## Functions (`sql/functions.sql`)

### `fn_project_progress(p_project_id INT)`
- Consumed by: `GET /reports/projects/{project_id}/progress`
- Returns: `DECIMAL(5,2)` percentage 0–100 of completed tasks in the project.
- Edge cases: no tasks → decide between NULL and 0 and be consistent.
- Unknown project id: returning NULL makes the API answer 404.

### `fn_milestone_progress(p_milestone_id INT)`
- Consumed by: `GET /reports/milestones/{milestone_id}/progress`
- Same semantics as above but scoped to one milestone's tasks.

## Procedures (`sql/procedures.sql`)

### `sp_complete_task(p_task_id INT)`
- Consumed by: `POST /tasks/{task_id}/complete`
- Purpose: mark a task as COMPLETED as an encapsulated database operation.
- Interaction with triggers: if the procedure updates `tasks.status`, the
  activity-log trigger should fire automatically; the procedure must not
  duplicate logging by hand.
- Business rules worth considering inside the procedure: what happens when the
  task is already COMPLETED or CANCELLED?

## Triggers (`sql/triggers.sql`)

### Task status audit trail
- Requirement: whenever a row in `tasks` has its `status` changed, insert into
  `activity_logs` (`task_id`, `action`, `old_status`, `new_status`,
  `created_at`).
- Timing decision (BEFORE vs AFTER) and action coverage (INSERT? UPDATE?) are
  the student's design decisions — document them in this file once written.

## Transactions

Planned composite operation (endpoint stub to be added):

- `POST /projects/with-milestone`: create a project **and** its first
  milestone atomically. If any step fails, nothing is persisted.
- Implementation belongs to the student, controlled either from FastAPI via
  the mysql.connector transaction API or inside a stored procedure.
- Concepts involved: START TRANSACTION / COMMIT / ROLLBACK, atomicity.

## JSON (`users.preferences`, Sub-CPMK-6)

- Column: `users.preferences JSON NULL` (already in `schema.sql`).
- Wired endpoints:
  - `PUT /users/{user_id}/preferences` stores an arbitrary JSON object (whole-blob write).
  - `GET /users/{id}` returns it.
- Student work: demonstrate extraction/modification against this column using
  MySQL JSON functions during evaluation (e.g., reading a single preference
  key). Suggested demo data shape: `{"theme": "dark", "notifications": true}`.

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
