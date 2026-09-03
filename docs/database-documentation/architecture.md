# Database Architecture

## Overview

MySQL 8.4 (InnoDB), database name `TaskManager`, provisioned by Docker Compose.
FastAPI talks to MySQL through `mysql.connector` with **no ORM**. Every request
opens one connection (`bismillah_mbd.database.get_db`) and closes it afterwards.

```
HTTP request → Pydantic validation → mysql.connector query → JSON response
```

Where a business rule or calculation belongs to the database, the API calls the
database object (view / function / procedure) instead of reimplementing the
logic in Python. See `dbm-features.md` for the exact contracts.

## Schema

Defined in `src/bismillah_mbd/sql/01-schema.sql`:

| Table | Purpose |
|---|---|
| `projects` | Top-level work containers |
| `milestones` | Phases of a project |
| `tasks` | Units of work inside a milestone |
| `users` | People who can be assigned tasks |
| `activity_logs` | Automatic audit trail of task status changes |

### Active database rules enforced by the schema

| Rule | Mechanism |
|---|---|
| Row identity | `PRIMARY KEY` on every table |
| One account per username/email | `UNIQUE` on `users.username`, `users.email` |
| Project deadline not before start date | `CHECK (deadline >= start_date)` |
| Task lifecycle values | `ENUM` columns for statuses/priority |
| Sensible defaults | `DEFAULT` on statuses, priority, timestamps |
| Milestone/task ownership | `NOT NULL` FKs |
| Delete project → milestones/tasks/logs disappear | FK `ON DELETE CASCADE` |
| Delete user → assignment becomes NULL | FK `ON DELETE SET NULL` |
| Automatic activity logging | Trigger (see `04-triggers.sql`, written by the student) |

## SQL Migration Files (Auto-Loaded)

All migrations are baked into the custom Docker image (`Dockerfile.mysql`) and
executed automatically on first container start via MySQL's
`/docker-entrypoint-initdb.d/` mechanism. **No manual SQL loading required.**

| Order | File | Purpose |
|---|---|---|
| 1 | `01-schema.sql` | Tables, PKs, FKs, constraints, CHECKs, ENUMs |
| 2 | `02-functions.sql` | `fn_get_project_progress`, `fn_get_milestone_progress` |
| 3 | `03-procedures.sql` | 21 stored procedures (CRUD, status transitions, reports) |
| 4 | `04-triggers.sql` | `trg_task_status_audit` → `activity_logs` |
| 5 | `05-views.sql` | `v_projects`, `v_overdue_tasks`, `v_assignee_workload` |
| 6 | `06-indexes.sql` | Performance indexes (student-identified) |
| 7 | `07-seeder.sql` | Optional test data |
| 8 | `08-user-access.sql` | Least-privilege grants for `app` user |

Views are loaded after functions because a view may call a function;
triggers come before views/indexes because indexes are best created after
initial data loading during optimization work;
permissions run last so all objects exist before grants.

## Nested Data via Multiple Result Sets (NEW)

Two procedures now return **multiple result sets** to provide hierarchical data in a single round-trip:

| Procedure | Result Set 1 | Result Set 2 |
|---|---|---|
| `sp_get_project_by_id` | Project row | Milestones for that project |
| `sp_get_milestone_by_id` | Milestone row | Tasks for that milestone |

**Benefits:**
- Single DB round-trip for nested data (project → milestones, milestone → tasks)
- No column duplication (unlike JOIN which repeats parent columns per child row)
- Clean separation maps directly to Pydantic models (`ProjectWithMilestonesResponse`, `MilestoneWithTasksResponse`)

**Python Pattern:**
```python
cur.callproc("sp_get_project_by_id", (project_id,))
results = list(cur.stored_results())
project = results[0].fetchone()
milestones = results[1].fetchall() if len(results) > 1 else []
project["milestones"] = milestones
```

**Endpoints Using This:**
- `GET /projects/{project_id}` → returns project with `milestones` array
- `GET /milestones/{milestone_id}` → returns milestone with `tasks` array

## Connection Configuration

Read from environment variables (see `.env.example`):

| Variable | Meaning | Default in compose |
|---|---|---|
| `DB_HOST` | MySQL host | `localhost` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | Database name | `TaskManager` |
| `DB_USER` | Application user | `app` |
| `DB_PASSWORD` | Application password | `app_password` |

Note: the `app` user created by the compose image gets privileges on the
database named by `MYSQL_DATABASE`. Since the app standardizes on
`TaskManager`, `compose.yaml` sets `MYSQL_DATABASE: TaskManager`.

## Least-Privilege Database User (`app`)

The `app` user is restricted to the minimum required operations:

| Permission | Objects |
|---|---|
| `EXECUTE` | All 21 stored procedures (`sp_create_*`, `sp_get_*`, `sp_list_*`, `sp_update_*`, `sp_delete_*`, `sp_complete_task`, `sp_update_task_status`) |
| `EXECUTE` | 2 functions (`fn_get_project_progress`, `fn_get_milestone_progress`) |
| `SELECT` | 3 views (`v_projects`, `v_overdue_tasks`, `v_assignee_workload`) |

**Revoked:** `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `INDEX` on all tables.

This enforces that all data access flows through stored procedures, views, and triggers — the `app` user cannot read or write tables directly.

See `src/bismillah_mbd/sql/08-user-access.sql` for the exact grant statements.
