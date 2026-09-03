# bismillah-mbd

Task Management System backend built to demonstrate Database Management
concepts (course project IF2514504). FastAPI + MySQL 8.4 via
`mysql.connector`, no ORM.

- Use Case Diagram: `docs/use-case-diagram/ucd.md`
- ERD: `docs/erd/erd.md`
- Database architecture: `docs/database-documentation/architecture.md`
- Database feature contracts (views/functions/procedures/triggers/transactions/JSON/indexes):
  `docs/database-documentation/dbm-features.md`

## Setup

Requirements: Docker, [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env          # connection settings used by the API
docker compose up -d          # start MySQL 8.4 (database TaskManager) — auto-runs all SQL migrations
uv sync                       # install Python dependencies
```

> **Note:** All SQL migrations (`01-schema.sql` through `08-user-access.sql`) are baked into the custom Docker image and run automatically on first container start. No manual SQL loading required.

Run the API:

```bash
uv run bismillah-mbd          # http://127.0.0.1:8000
# or, with auto-reload during development:
uv run fastapi dev
```

Interactive API docs: http://127.0.0.1:8000/docs

## Database User Permissions (Least Privilege)

The `app` database user is restricted to **execute stored procedures/functions** and **select from views** only — no direct table access (SELECT/INSERT/UPDATE/DELETE on tables is revoked). See `src/bismillah_mbd/sql/08-user-access.sql` and `docs/database-documentation/architecture.md`.

## API Overview

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /users/{id}`, `PUT /users/{id}/preferences` |
| Manage Project | CRUD under `POST/GET/PUT/DELETE /projects`, `POST /projects/with-milestone/create` (project + first milestone atomically) |
| Plan Project | `POST /projects/{project_id}/milestone/create`, CRUD under `/milestones`, task creation under `/milestones/{milestone_id}/tasks/create` |
| Execute Tasks | `POST /tasks/{id}/start`, `/complete` (calls `sp_complete_task`), `/cancel`, `PUT /tasks/{id}/update` |
| Monitor Project | `GET /reports/projects/{id}/progress`, `GET /reports/milestones/{id}/progress`, `GET /reports/tasks/overdue`, `GET /reports/workload` |

Endpoints that depend on student-written database objects return HTTP 501
until those objects are created; see `dbm-features.md`.

## Project Layout

```
src/bismillah_mbd/
├── main.py            FastAPI app + entrypoint
├── database.py        connection management (mysql.connector)
├── schemas.py         shared Pydantic models (Create/Update/Response)
├── routes/            thin HTTP layer (auth, projects, milestones, tasks, reports)
└── sql/               schema + DBM feature SQL (views/functions/procedures/triggers/indexes/permissions)
```
