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

Defined in `src/bismillah_mbd/sql/schema.sql`:

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
| Automatic activity logging | Trigger (see `triggers.sql`, written by the student) |

## SQL file load order

Execute in this order (later files may depend on earlier ones):

1. `schema.sql`
2. `functions.sql`
3. `procedures.sql`
4. `triggers.sql`
5. `views.sql`
6. `indexes.sql`

Views are loaded after functions because a view may call a function;
triggers come before views/indexes because indexes are best created after
initial data loading during optimization work.

Example (from a repo root shell):

```bash
docker compose up -d
docker exec -i project-management-mysql mysql -uroot -proot < src/bismillah_mbd/sql/schema.sql
# repeat for each file in the order above
```

## Connection configuration

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
