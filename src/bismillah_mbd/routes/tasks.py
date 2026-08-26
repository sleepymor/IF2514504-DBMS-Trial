from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error as MySQLError, MySQLConnection
from pydantic import BaseModel, Field

from bismillah_mbd.database import get_db

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskCreate(BaseModel):
    milestone_id: int
    assignee_id: int | None = None
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] = "LOW"
    deadline: date


class TaskUpdate(BaseModel):
    assignee_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] | None = None
    deadline: date | None = None


class TaskResponse(BaseModel):
    id: int
    milestone_id: int
    assignee_id: int | None
    name: str
    description: str | None
    priority: str
    status: str
    deadline: date
    created_at: datetime
    updated_at: datetime


def fetch_task(conn: MySQLConnection, task_id: int) -> dict:
    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        task = cur.fetchone()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(payload: TaskCreate, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (milestone_id, assignee_id, name, description, priority, deadline) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    payload.milestone_id,
                    payload.assignee_id,
                    payload.name,
                    payload.description,
                    payload.priority,
                    payload.deadline,
                ),
            )
            new_id = cur.lastrowid
        conn.commit()
    except MySQLError as e:
        if e.errno == 1452:
            raise HTTPException(
                status_code=404, detail="Milestone or assignee not found"
            ) from e
        raise
    return fetch_task(conn, new_id)


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    milestone_id: int | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    status: Literal["TODO", "IN_PROGRESS", "COMPLETED", "CANCELLED"] | None = Query(default=None),
    conn: MySQLConnection = Depends(get_db),
):
    filters = []
    params = []
    if milestone_id is not None:
        filters.append("milestone_id = %s")
        params.append(milestone_id)
    if assignee_id is not None:
        filters.append("assignee_id = %s")
        params.append(assignee_id)
    if status is not None:
        filters.append("status = %s")
        params.append(status)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    with conn.cursor(dictionary=True) as cur:
        cur.execute(f"SELECT * FROM tasks {where} ORDER BY id", tuple(params))
        return cur.fetchall()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    return fetch_task(conn, task_id)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    assignments = ", ".join(f"{column} = %s" for column in data)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE tasks SET {assignments} WHERE id = %s",
                (*data.values(), task_id),
            )
        conn.commit()
    except MySQLError as e:
        if e.errno == 1452:
            raise HTTPException(status_code=404, detail="Assignee not found") from e
        raise
    return fetch_task(conn, task_id)


@router.post("/{task_id}/start", response_model=TaskResponse)
def start_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    with conn.cursor() as cur:
        cur.execute("UPDATE tasks SET status = 'IN_PROGRESS' WHERE id = %s", (task_id,))
    conn.commit()
    return fetch_task(conn, task_id)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_complete_task", (task_id,))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_complete_task does not exist yet - see src/bismillah_mbd/sql/procedures.sql",
            ) from e
        raise
    return fetch_task(conn, task_id)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
def cancel_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    with conn.cursor() as cur:
        cur.execute("UPDATE tasks SET status = 'CANCELLED' WHERE id = %s", (task_id,))
    conn.commit()
    return fetch_task(conn, task_id)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
