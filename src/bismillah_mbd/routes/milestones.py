from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error as MySQLError, MySQLConnection
from pydantic import BaseModel, Field

from bismillah_mbd.database import get_db

router = APIRouter(prefix="/milestones", tags=["Milestones"])

MilestoneStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED"]


class MilestoneCreate(BaseModel):
    project_id: int
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    deadline: date
    status: MilestoneStatus = "PENDING"


class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    deadline: date | None = None
    status: MilestoneStatus | None = None


class MilestoneResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None
    deadline: date
    status: str
    created_at: datetime
    updated_at: datetime


def fetch_milestone(conn: MySQLConnection, milestone_id: int) -> dict:
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_get_milestone_by_id", (milestone_id,))
            for result in cur.stored_results():
                milestone = result.fetchone()
                break
            else:
                milestone = None
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_get_milestone_by_id does not exist yet - see src/bismillah_mbd/sql/procedures.sql",
            ) from e
        raise
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.post("/", response_model=MilestoneResponse, status_code=201)
def create_milestone(payload: MilestoneCreate, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_create_milestone", (
                payload.project_id,
                payload.name,
                payload.description,
                payload.deadline,
                payload.status,
            ))
            for result in cur.stored_results():
                row = result.fetchone()
                if row:
                    new_id = row[0]
                    break
            else:
                new_id = cur.lastrowid
        conn.commit()
    except MySQLError as e:
        if e.errno == 1452:
            raise HTTPException(status_code=404, detail="Project not found") from e
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_create_milestone does not exist yet - see src/bismillah_mbd/sql/procedures.sql",
            ) from e
        raise
    return fetch_milestone(conn, new_id)


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
                detail="sp_list_milestones does not exist yet - see src/bismillah_mbd/sql/procedures.sql",
            ) from e
        raise
    return []


@router.get("/{milestone_id}", response_model=MilestoneResponse)
def get_milestone(milestone_id: int, conn: MySQLConnection = Depends(get_db)):
    return fetch_milestone(conn, milestone_id)


@router.put("/{milestone_id}", response_model=MilestoneResponse)
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
                detail="sp_update_milestone does not exist yet - see src/bismillah_mbd/sql/procedures.sql",
            ) from e
        raise
    return fetch_milestone(conn, milestone_id)


@router.delete("/{milestone_id}", status_code=204)
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
                detail="sp_delete_milestone does not exist yet - see src/bismillah_mbd/sql/procedures.sql",
            ) from e
        raise
