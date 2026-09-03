USE TaskManager;

-- Revoke all default table privileges from app user
REVOKE SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX 
ON TaskManager.* FROM 'app'@'%';

GRANT EXECUTE ON PROCEDURE TaskManager.sp_create_user TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_create_project TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_create_project_with_milestone TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_create_milestone TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_create_task TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_update_task_status TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_complete_task TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_get_user_by_id TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_get_user_by_credentials TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_get_project_by_id TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_get_milestone_by_id TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_list_milestones TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_get_task_by_id TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_list_tasks TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_update_project TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_update_milestone TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_update_task TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_delete_project TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_delete_milestone TO 'app'@'%';
GRANT EXECUTE ON PROCEDURE TaskManager.sp_delete_task TO 'app'@'%';

GRANT EXECUTE ON FUNCTION TaskManager.fn_get_project_progress TO 'app'@'%';
GRANT EXECUTE ON FUNCTION TaskManager.fn_get_milestone_progress TO 'app'@'%';

GRANT SELECT ON TaskManager.v_projects TO 'app'@'%';
GRANT SELECT ON TaskManager.v_overdue_tasks TO 'app'@'%';
GRANT SELECT ON TaskManager.v_assignee_workload TO 'app'@'%';

FLUSH PRIVILEGES;