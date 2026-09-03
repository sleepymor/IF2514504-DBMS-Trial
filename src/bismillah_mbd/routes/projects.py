from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error as MySQLError, MySQLConnection

from bismillah_mbd.database import get_db
from bismillah_mbd.schemas import (
    MilestoneCreate,
    MilestoneCreateNoProject,
    MilestoneInline,
    MilestoneResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithMilestoneCreate,
    ProjectWithMilestonesResponse,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


def fetch_project(conn: MySQLConnection, project_id: int) -> dict:
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_get_project_by_id", (project_id,))
            results = list(cur.stored_results())
            project = results[0].fetchone() if results else None
            milestones = results[1].fetchall() if len(results) > 1 else []
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_get_project_by_id does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    project["milestones"] = milestones
    return project


@router.post("/create", response_model=ProjectResponse, status_code=201)
def create_project(payload: ProjectCreate, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            args = (
                payload.name,
                payload.description,
                payload.start_date,
                payload.deadline,
                payload.status,
                0,
            )
            result = cur.callproc("sp_create_project", args)
            new_id = result[5]
        conn.commit()
    except MySQLError as e:
        if e.errno == 3819:
            raise HTTPException(status_code=400, detail="Deadline cannot be before start date") from e
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_create_project does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_project(conn, new_id)


@router.post("/with-milestone/create", response_model=ProjectResponse, status_code=201)
def create_project_with_milestone(
    payload: ProjectWithMilestoneCreate, conn: MySQLConnection = Depends(get_db)
):
    try:
        with conn.cursor() as cur:
            args = (
                payload.name,
                payload.description,
                payload.start_date,
                payload.deadline,
                payload.status,
                payload.milestone.name,
                payload.milestone.description,
                payload.milestone.deadline,
                payload.milestone.status,
                0,
                0,
            )
            result = cur.callproc("sp_create_project_with_milestone", args)
            new_id = result[9]
        conn.commit()
    except MySQLError as e:
        if e.errno == 3819:
            raise HTTPException(status_code=400, detail="Deadline cannot be before start date") from e
        if e.errno == 1452:
            raise HTTPException(status_code=404, detail="Project or milestone FK violation") from e
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_create_project_with_milestone does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_project(conn, new_id)


@router.post("/{project_id}/milestone/create", response_model=MilestoneResponse, status_code=201)
def create_milestone(
    project_id: int, payload: MilestoneCreateNoProject, conn: MySQLConnection = Depends(get_db)
):
    try:
        with conn.cursor() as cur:
            args = (
                project_id,
                payload.name,
                payload.description,
                payload.deadline,
                payload.status,
                0,
            )
            result = cur.callproc("sp_create_milestone", args)
            new_id = result[5]
        conn.commit()
    except MySQLError as e:
        if e.errno == 1452:
            raise HTTPException(status_code=404, detail="Project not found") from e
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_create_milestone does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_milestone(conn, new_id)


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
                detail="sp_get_milestone_by_id does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.get("/", response_model=list[ProjectResponse])
def list_projects(conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur: 
            cur.execute("""
                SELECT id, name, description, start_date, deadline, status, created_at, updated_at
                FROM v_projects
            """)
            return cur.fetchall()
    except MySQLError as e:
        if e.errno == 1146:
            raise HTTPException(
                status_code=501,
                detail="v_projects view does not exist yet - see src/bismillah_mbd/sql/05-views.sql",
            ) from e
        raise
    return []


@router.get("/{project_id}", response_model=ProjectWithMilestonesResponse)
def get_project(project_id: int, conn: MySQLConnection = Depends(get_db)):
    return fetch_project(conn, project_id)


@router.put("/{project_id}/update", response_model=ProjectResponse)
def update_project(
    project_id: int, payload: ProjectUpdate, conn: MySQLConnection = Depends(get_db)
):
    fetch_project(conn, project_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    # Full update - get current values for missing fields
    current = fetch_project(conn, project_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_update_project", (
                project_id,
                data.get("name", current["name"]),
                data.get("description", current["description"]),
                data.get("start_date", current["start_date"]),
                data.get("deadline", current["deadline"]),
                data.get("status", current["status"]),
            ))
        conn.commit()
    except MySQLError as e:
        if e.errno == 3819:
            raise HTTPException(status_code=400, detail="Deadline cannot be before start date") from e
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_update_project does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_project(conn, project_id)


@router.delete("/{project_id}/destroy", status_code=204)
def delete_project(project_id: int, conn: MySQLConnection = Depends(get_db)):
    fetch_project(conn, project_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_delete_project", (project_id,))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_delete_project does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
