from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error as MySQLError, MySQLConnection
from pydantic import BaseModel, Field

from bismillah_mbd.database import get_db

router = APIRouter(prefix="/projects", tags=["Projects"])

ProjectStatus = Literal["PLANNED", "ACTIVE", "COMPLETED", "CANCELLED"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    start_date: date
    deadline: date
    status: ProjectStatus = "PLANNED"


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    start_date: date | None = None
    deadline: date | None = None
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    start_date: date
    deadline: date
    status: str
    created_at: datetime
    updated_at: datetime


class MilestoneInline(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    deadline: date


class ProjectWithMilestoneCreate(ProjectCreate):
    milestone: MilestoneInline


def fetch_project(conn: MySQLConnection, project_id: int) -> dict:
    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = cur.fetchone()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(payload: ProjectCreate, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO projects (name, description, start_date, deadline, status) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    payload.name,
                    payload.description,
                    payload.start_date,
                    payload.deadline,
                    payload.status,
                ),
            )
            new_id = cur.lastrowid
        conn.commit()
    except MySQLError as e:
        if e.errno == 3819:
            raise HTTPException(status_code=400, detail="Deadline cannot be before start date") from e
        raise
    return fetch_project(conn, new_id)


@router.post("/with-milestone", status_code=501)
def create_project_with_milestone(
    payload: "ProjectWithMilestoneCreate", conn: MySQLConnection = Depends(get_db)
):
    raise HTTPException(
        status_code=501,
        detail=(
            "To be implemented using MySQL transactions - "
            "see docs/database-documentation/dbm-features.md"
        ),
    )


@router.get("/", response_model=list[ProjectResponse])
def list_projects(conn: MySQLConnection = Depends(get_db)):
    with conn.cursor(dictionary=True) as cur:
        cur.execute("SELECT * FROM projects ORDER BY id")
        return cur.fetchall()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, conn: MySQLConnection = Depends(get_db)):
    return fetch_project(conn, project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int, payload: ProjectUpdate, conn: MySQLConnection = Depends(get_db)
):
    fetch_project(conn, project_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    assignments = ", ".join(f"{column} = %s" for column in data)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE projects SET {assignments} WHERE id = %s",
                (*data.values(), project_id),
            )
        conn.commit()
    except MySQLError as e:
        if e.errno == 3819:
            raise HTTPException(status_code=400, detail="Deadline cannot be before start date") from e
        raise
    return fetch_project(conn, project_id)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_project(conn, project_id)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
    conn.commit()
