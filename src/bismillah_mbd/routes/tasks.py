from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error as MySQLError, MySQLConnection

from bismillah_mbd.database import get_db
from bismillah_mbd.schemas import TaskResponse, TaskUpdate

router = APIRouter(prefix="/task", tags=["Tasks"])


def fetch_task(conn: MySQLConnection, task_id: int) -> dict:
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_get_task_by_id", (task_id,))
            for result in cur.stored_results():
                task = result.fetchone()
                break
            else:
                task = None
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_get_task_by_id does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    milestone_id: int | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    status: Literal["TODO", "IN_PROGRESS", "COMPLETED", "CANCELLED"] | None = Query(default=None),
    conn: MySQLConnection = Depends(get_db),
):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_list_tasks", (milestone_id, assignee_id, status))
            for result in cur.stored_results():
                return result.fetchall()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_list_tasks does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return []


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    return fetch_task(conn, task_id)


@router.put("/{task_id}/update", response_model=TaskResponse)
def update_task(task_id: int, payload: TaskUpdate, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    current = fetch_task(conn, task_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_update_task", (
                task_id,
                data.get("milestone_id", current["milestone_id"]),
                data.get("assignee_id", current["assignee_id"]),
                data.get("name", current["name"]),
                data.get("description", current["description"]),
                data.get("priority", current["priority"]),
                data.get("deadline", current["deadline"]),
                data.get("status", current["status"]),
            ))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1452:
            raise HTTPException(status_code=404, detail="Assignee or milestone not found") from e
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_update_task does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_task(conn, task_id)


@router.post("/{task_id}/start", response_model=TaskResponse)
def start_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_update_task_status", (
                task_id,
                'IN_PROGRESS',
                'start'
            ))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_update_task_status does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
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
                detail="sp_complete_task does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_task(conn, task_id)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
def cancel_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_update_task_status", (
                task_id,
                'CANCELLED',
                'cancel'
            ))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_update_task_status does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_task(conn, task_id)


@router.delete("/{task_id}/destroy", status_code=204)
def delete_task(task_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_task(conn, task_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_delete_task", (task_id,))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_delete_task does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
