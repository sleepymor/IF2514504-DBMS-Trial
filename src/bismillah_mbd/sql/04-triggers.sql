USE TaskManager;

DELIMITER //

-- Trigger: trg_task_status_audit
-- Timing: AFTER UPDATE
-- Table: tasks
-- Purpose: Automatically log task status changes to activity_logs table
-- Fires: Only when tasks.status column value changes (OLD.status <> NEW.status)
-- Inserts: task_id, action ('status_change'), old_status, new_status, created_at (auto)

DROP TRIGGER IF EXISTS trg_task_status_audit//

CREATE TRIGGER trg_task_status_audit
AFTER UPDATE ON tasks
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO activity_logs (task_id, action, old_status, new_status)
        VALUES (NEW.id, 'status_change', OLD.status, NEW.status);
    END IF;
END//

DELIMITER ;