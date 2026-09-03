USE TaskManager;

DELIMITER //

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