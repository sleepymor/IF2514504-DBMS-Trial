from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from mysql.connector import Error as MySQLError, MySQLConnection

from bismillah_mbd.database import get_db
from bismillah_mbd.schemas import (
    MilestoneResponse,
    MilestoneStatus,
    MilestoneUpdate,
    MilestoneWithTasksResponse,
    TaskCreate,
    TaskResponse,
)

router = APIRouter(prefix="/milestones", tags=["Milestones"])

def fetch_milestone(conn: MySQLConnection, milestone_id: int) -> dict:
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_get_milestone_by_id", (milestone_id,))
            results = list(cur.stored_results())
            milestone = results[0].fetchone() if results else None
            tasks = results[1].fetchall() if len(results) > 1 else []
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_get_milestone_by_id does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    milestone["tasks"] = tasks
    return milestone

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



@router.get("/", response_model=list[MilestoneResponse])
def list_milestones(
    project_id: int | None = Query(default=None),
    conn: MySQLConnection = Depends(get_db),
):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_list_milestones", (project_id,))
            for result in cur.stored_results():
                return result.fetchall()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_list_milestones does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return []


@router.get("/{milestone_id}", response_model=MilestoneWithTasksResponse)
def get_milestone(milestone_id: int, conn: MySQLConnection = Depends(get_db)):
    return fetch_milestone(conn, milestone_id)


@router.put("/{milestone_id}/update", response_model=MilestoneResponse)
def update_milestone(
    milestone_id: int, payload: MilestoneUpdate, conn: MySQLConnection = Depends(get_db)
):
    fetch_milestone(conn, milestone_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    current = fetch_milestone(conn, milestone_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_update_milestone", (
                milestone_id,
                data.get("name", current["name"]),
                data.get("description", current["description"]),
                data.get("deadline", current["deadline"]),
                data.get("status", current["status"]),
            ))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_update_milestone does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_milestone(conn, milestone_id)


@router.delete("/{milestone_id}/destroy", status_code=204)
def delete_milestone(milestone_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_milestone(conn, milestone_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_delete_milestone", (milestone_id,))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_delete_milestone does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise

@router.post("/{milestone_id}/tasks/create", response_model=TaskResponse, status_code=201)
def create_task(milestone_id: int, payload: TaskCreate, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            args = (
                milestone_id,
                payload.assignee_id,
                payload.name,
                payload.description,
                payload.priority,
                payload.deadline,
                0,
            )
            result = cur.callproc("sp_create_task", args)
            new_id = result[6]
        conn.commit()
    except MySQLError as e:
        if e.errno == 1452:
            raise HTTPException(
                status_code=404, detail="Milestone or assignee not found"
            ) from e
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_create_task does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_task(conn, new_id)