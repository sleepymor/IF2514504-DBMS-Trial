# Use Case Diagram

Actor: **User**

Main business use cases (exactly four):

1. Manage Project
2. Plan Project
3. Execute Tasks
4. Monitor Project

Supporting use case (not counted as a main business use case):

- Authenticate User

```mermaid
flowchart LR
    User([fa:fa-user User])

    subgraph TaskManagementSystem["Task Management System"]
        UC1(["Manage Project"])
        UC2(["Plan Project"])
        UC3(["Execute Tasks"])
        UC4(["Monitor Project"])
        UC5(["Authenticate User"])
    end

    User --- UC1
    User --- UC2
    User --- UC3
    User --- UC4
    User -.->|"include"| UC5
```

Notes:

- CRUD operations (create/update/delete project, etc.) are **not** modeled as separate
  top-level use cases; they are the internal steps of the four main use cases.
- `Authenticate User` is drawn with an `include` relationship because every other
  use case assumes an identified user, but it remains a supporting use case.
