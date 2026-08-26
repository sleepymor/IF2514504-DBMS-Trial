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
docker compose up -d          # start MySQL 8.4 (database TaskManager)
uv sync                       # install Python dependencies
```

Load the SQL files in order (later files may depend on earlier ones):

```bash
docker exec -i project-management-mysql mysql -uroot -proot < src/bismillah_mbd/sql/schema.sql
docker exec -i project-management-mysql mysql -uroot -proot < src/bismillah_mbd/sql/functions.sql
docker exec -i project-management-mysql mysql -uroot -proot < src/bismillah_mbd/sql/procedures.sql
docker exec -i project-management-mysql mysql -uroot -proot < src/bismillah_mbd/sql/triggers.sql
docker exec -i project-management-mysql mysql -uroot -proot < src/bismillah_mbd/sql/views.sql
docker exec -i project-management-mysql mysql -uroot -proot < src/bismillah_mbd/sql/indexes.sql
```

Run the API:

```bash
uv run bismillah-mbd          # http://127.0.0.1:8000
# or, with auto-reload during development:
uv run fastapi dev
```

Interactive API docs: http://127.0.0.1:8000/docs

## API overview

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /users/{id}`, `PUT /users/{id}/preferences` |
| Manage Project | CRUD under `POST/GET/PUT/DELETE /projects` |
| Plan Project | CRUD under `/milestones`, task creation/update under `/tasks` |
| Execute Tasks | `POST /tasks/{id}/start`, `/complete` (calls `sp_complete_task`), `/cancel` |
| Monitor Project | `GET /reports/projects/{id}/progress`, `GET /reports/milestones/{id}/progress`, `GET /reports/tasks/overdue`, `GET /reports/workload` |

Endpoints that depend on student-written database objects return HTTP 501
until those objects are created; see `dbm-features.md`.

## Project layout

```
src/bismillah_mbd/
├── main.py            FastAPI app + entrypoint
├── database.py        connection management (mysql.connector)
├── routes/            thin HTTP layer (auth, projects, milestones, tasks, reports)
└── sql/               schema + DBM feature SQL (views/functions/procedures/triggers/indexes)
```
