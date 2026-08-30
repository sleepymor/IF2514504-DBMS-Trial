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
            cur.execute("SELECT fn_get_project_progress(%s)", (project_id,))
            row = cur.fetchone()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="fn_get_project_progress function does not exist yet - see src/bismillah_mbd/sql/procedures.sql",
            ) from e
        raise
    if row is None or row[0] is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project_id": project_id, "progress_percentage": row[0]}


@router.get("/milestones/{milestone_id}/progress")
def milestone_progress(milestone_id: int, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT fn_get_milestone_progress(%s)", (milestone_id,))
            row = cur.fetchone()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="fn_get_milestone_progress function does not exist yet - see src/bismillah_mbd/sql/procedures.sql",
            ) from e
        raise
    if row is None or row[0] is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {"milestone_id": milestone_id, "progress_percentage": row[0]}


@router.get("/tasks/overdue")
def overdue_tasks(conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("""
                SELECT task_id, task_name, status, deadline, priority, milestone_id, milestone_name, project_id, project_name, assignee_id
                FROM v_overdue_tasks
            """)
            return cur.fetchall()
    except MySQLError as e:
        if e.errno == 1146:
            raise HTTPException(
                status_code=501,
                detail="v_overdue_tasks view does not exist yet - see src/bismillah_mbd/sql/views.sql",
            ) from e
        raise
    return []


@router.get("/workload")
def assignee_workload(conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("""
                SELECT assignee_id, assignee_username, assignee_email, open_task_count, overdue_task_count
                FROM v_assignee_workload
            """)
            return cur.fetchall()
    except MySQLError as e:
        if e.errno == 1146:
            raise HTTPException(
                status_code=501,
                detail="v_assignee_workload view does not exist yet - see src/bismillah_mbd/sql/views.sql",
            ) from e
        raise
    return []
