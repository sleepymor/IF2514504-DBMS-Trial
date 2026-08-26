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
    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT * FROM milestones WHERE id = %s", (milestone_id,))
        milestone = cur.fetchone()
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.post("/", response_model=MilestoneResponse, status_code=201)
def create_milestone(payload: MilestoneCreate, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO milestones (project_id, name, description, deadline, status) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    payload.project_id,
                    payload.name,
                    payload.description,
                    payload.deadline,
                    payload.status,
                ),
            )
            new_id = cur.lastrowid
        conn.commit()
    except MySQLError as e:
        if e.errno == 1452:
            raise HTTPException(status_code=404, detail="Project not found") from e
        raise
    return fetch_milestone(conn, new_id)


@router.get("/", response_model=list[MilestoneResponse])
def list_milestones(
    project_id: int | None = Query(default=None),
    conn: MySQLConnection = Depends(get_db),
):
    with conn.cursor(dictionary=True) as cur:
        if project_id is None:
            cur.execute("SELECT * FROM milestones ORDER BY id")
        else:
            cur.execute("SELECT * FROM milestones WHERE project_id = %s ORDER BY id", (project_id,))
        return cur.fetchall()


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
    assignments = ", ".join(f"{column} = %s" for column in data)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE milestones SET {assignments} WHERE id = %s",
            (*data.values(), milestone_id),
        )
    conn.commit()
    return fetch_milestone(conn, milestone_id)


@router.delete("/{milestone_id}", status_code=204)
def delete_milestone(milestone_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_milestone(conn, milestone_id)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM milestones WHERE id = %s", (milestone_id,))
    conn.commit()
