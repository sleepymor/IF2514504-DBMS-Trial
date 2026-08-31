USE TaskManager;

-- Scalar Function: fn_get_project_progress
-- Calculates project completion percentage based on task status
DROP FUNCTION IF EXISTS fn_get_project_progress;
CREATE FUNCTION fn_get_project_progress(p_project_id INT)
RETURNS DECIMAL(5,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_total INT DEFAULT 0;
    DECLARE v_completed INT DEFAULT 0;

    SELECT COUNT(*) INTO v_total
    FROM tasks t
    JOIN milestones m ON t.milestone_id = m.id
    WHERE m.project_id = p_project_id;

    IF v_total = 0 THEN
        RETURN NULL;
    END IF;

    SELECT COUNT(*) INTO v_completed
    FROM tasks t
    JOIN milestones m ON t.milestone_id = m.id
    WHERE m.project_id = p_project_id AND t.status = 'COMPLETED';

    RETURN ROUND((v_completed / v_total) * 100, 2);
END;

-- Scalar Function: fn_get_milestone_progress
-- Calculates milestone completion percentage based on task status
DROP FUNCTION IF EXISTS fn_get_milestone_progress;
CREATE FUNCTION fn_get_milestone_progress(p_milestone_id INT)
RETURNS DECIMAL(5,2)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE v_total INT DEFAULT 0;
    DECLARE v_completed INT DEFAULT 0;

    SELECT COUNT(*) INTO v_total FROM tasks WHERE milestone_id = p_milestone_id;

    IF v_total = 0 THEN
        RETURN NULL;
    END IF;

    SELECT COUNT(*) INTO v_completed
    FROM tasks
    WHERE milestone_id = p_milestone_id AND status = 'COMPLETED';

    RETURN ROUND((v_completed / v_total) * 100, 2);
END;