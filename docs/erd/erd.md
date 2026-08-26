# Entity Relationship Diagram

The diagram matches `src/bismillah_mbd/sql/schema.sql` exactly.

Relationships implemented by foreign keys:

| Relationship | FK column | On delete |
|---|---|---|
| projects 1:N milestones | milestones.project_id | CASCADE |
| milestones 1:N tasks | tasks.milestone_id | CASCADE |
| users 1:N tasks (assignment) | tasks.assignee_id (nullable) | SET NULL |
| tasks 1:N activity_logs | activity_logs.task_id | CASCADE |

`tasks.assignee_id` is nullable: deleting a user does not delete their tasks,
the assignment becomes NULL.

```mermaid
erDiagram
    USERS ||--o{ TASKS : "is assigned"
    PROJECTS ||--o{ MILESTONES : "contains"
    MILESTONES ||--o{ TASKS : "contains"
    TASKS ||--o{ ACTIVITY_LOGS : "records"

    USERS {
        int id PK
        varchar username UK
        varchar email UK
        varchar password_hash
        json preferences "nullable, Sub-CPMK-6"
        timestamp created_at
    }

    PROJECTS {
        int id PK
        varchar name
        text description
        date start_date
        date deadline "CHECK deadline >= start_date"
        enum status "PLANNED ACTIVE COMPLETED CANCELLED"
        timestamp created_at
        timestamp updated_at
    }

    MILESTONES {
        int id PK
        int project_id FK
        varchar name
        text description
        date deadline
        enum status "PENDING IN_PROGRESS COMPLETED"
        timestamp created_at
        timestamp updated_at
    }

    TASKS {
        int id PK
        int milestone_id FK
        int assignee_id FK "nullable"
        varchar name
        text description
        enum priority "LOW MEDIUM HIGH URGENT"
        enum status "TODO IN_PROGRESS COMPLETED CANCELLED"
        date deadline
        timestamp created_at
        timestamp updated_at
    }

    ACTIVITY_LOGS {
        int id PK
        int task_id FK
        varchar action
        varchar old_status
        varchar new_status
        timestamp created_at
    }
```
