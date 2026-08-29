from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error as MySQLError, MySQLConnection

from bismillah_mbd.database import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


def translate_reporting_error(e: MySQLError) -> HTTPException:
    if e.errno == 1305:
        return HTTPException(
            status_code=501,
            detail="Database procedure not created yet - see src/bismillah_mbd/sql/procedures.sql",
        )
    return HTTPException(status_code=500, detail=e.msg)


@router.get("/projects/{project_id}/progress")
def project_progress(project_id: int, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_get_project_progress", (project_id,))
            for result in cur.stored_results():
                row = result.fetchone()
                break
            else:
                row = None
    except MySQLError as e:
        raise translate_reporting_error(e) from e
    if row is None or row[0] is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "progress_percentage": row[0]}


@router.get("/milestones/{milestone_id}/progress")
def milestone_progress(milestone_id: int, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_get_milestone_progress", (milestone_id,))
            for result in cur.stored_results():
                row = result.fetchone()
                break
            else:
                row = None
    except MySQLError as e:
        raise translate_reporting_error(e) from e
    if row is None or row[0] is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {"milestone_id": milestone_id, "progress_percentage": row[0]}


@router.get("/tasks/overdue")
def overdue_tasks(conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_list_overdue_tasks", ())
            for result in cur.stored_results():
                return result.fetchall()
    except MySQLError as e:
        raise translate_reporting_error(e) from e
    return []


@router.get("/workload")
def assignee_workload(conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_list_assignee_workload", ())
            for result in cur.stored_results():
                return result.fetchall()
    except MySQLError as e:
        raise translate_reporting_error(e) from e
    return []
