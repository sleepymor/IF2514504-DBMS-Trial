from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error as MySQLError, MySQLConnection

from bismillah_mbd.database import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


def translate_reporting_error(e: MySQLError) -> HTTPException:
    if e.errno == 1305:
        return HTTPException(
            status_code=501,
            detail="Database function not created yet - see src/bismillah_mbd/sql/functions.sql",
        )
    if e.errno == 1146:
        return HTTPException(
            status_code=501,
            detail="Database view not created yet - see src/bismillah_mbd/sql/views.sql",
        )
    return HTTPException(status_code=500, detail=e.msg)


@router.get("/projects/{project_id}/progress")
def project_progress(project_id: int, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT fn_project_progress(%s) AS progress_percentage", (project_id,))
            row = cur.fetchone()
    except MySQLError as e:
        raise translate_reporting_error(e) from e
    if row is None or row["progress_percentage"] is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "progress_percentage": row["progress_percentage"]}


@router.get("/milestones/{milestone_id}/progress")
def milestone_progress(milestone_id: int, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT fn_milestone_progress(%s) AS progress_percentage", (milestone_id,))
            row = cur.fetchone()
    except MySQLError as e:
        raise translate_reporting_error(e) from e
    if row is None or row["progress_percentage"] is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {"milestone_id": milestone_id, "progress_percentage": row["progress_percentage"]}


@router.get("/tasks/overdue")
def overdue_tasks(conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT * FROM v_overdue_tasks ORDER BY deadline")
            return cur.fetchall()
    except MySQLError as e:
        raise translate_reporting_error(e) from e


@router.get("/workload")
def assignee_workload(conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT * FROM v_assignee_workload ORDER BY assignee_id")
            return cur.fetchall()
    except MySQLError as e:
        raise translate_reporting_error(e) from e
