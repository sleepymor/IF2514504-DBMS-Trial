USE TaskManager;

-- CREATE Operations

DROP PROCEDURE IF EXISTS sp_create_user;
CREATE PROCEDURE sp_create_user(
    IN p_username VARCHAR(50),
    IN p_email VARCHAR(150),
    IN p_password_hash VARCHAR(255),
    OUT p_user_id INT
)
BEGIN
    INSERT INTO users (username, email, password_hash)
    VALUES (p_username, p_email, p_password_hash);
    SET p_user_id = LAST_INSERT_ID();
END;

DROP PROCEDURE IF EXISTS sp_create_project;
CREATE PROCEDURE sp_create_project(
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_start_date DATE,
    IN p_deadline DATE,
    IN p_status ENUM('PLANNED','ACTIVE','COMPLETED','CANCELLED'),
    OUT p_project_id INT
)
BEGIN
    INSERT INTO projects (name, description, start_date, deadline, status)
    VALUES (p_name, p_description, p_start_date, p_deadline, p_status);
    SET p_project_id = LAST_INSERT_ID();
END;

DROP PROCEDURE IF EXISTS sp_create_project_with_milestone;
CREATE PROCEDURE sp_create_project_with_milestone(
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_start_date DATE,
    IN p_deadline DATE,
    IN p_status ENUM('PLANNED','ACTIVE','COMPLETED','CANCELLED'),
    IN p_milestone_name VARCHAR(150),
    IN p_milestone_description TEXT,
    IN p_milestone_deadline DATE,
    IN p_milestone_status ENUM('PENDING','IN_PROGRESS','COMPLETED'),
    OUT p_project_id INT,
    OUT p_milestone_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO projects (name, description, start_date, deadline, status)
    VALUES (p_name, p_description, p_start_date, p_deadline, p_status);
    SET p_project_id = LAST_INSERT_ID();

    INSERT INTO milestones (project_id, name, description, deadline, status)
    VALUES (p_project_id, p_milestone_name, p_milestone_description, p_milestone_deadline, p_milestone_status);
    SET p_milestone_id = LAST_INSERT_ID();
    COMMIT;
END;

DROP PROCEDURE IF EXISTS sp_create_milestone;
CREATE PROCEDURE sp_create_milestone(
    IN p_project_id INT,
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_deadline DATE,
    IN p_status ENUM('PENDING','IN_PROGRESS','COMPLETED'),
    OUT p_milestone_id INT
)
BEGIN
    INSERT INTO milestones (project_id, name, description, deadline, status)
    VALUES (p_project_id, p_name, p_description, p_deadline, p_status);
    SET p_milestone_id = LAST_INSERT_ID();
END;

DROP PROCEDURE IF EXISTS sp_create_task;
CREATE PROCEDURE sp_create_task(
    IN p_milestone_id INT,
    IN p_assignee_id INT,
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_priority ENUM('LOW','MEDIUM','HIGH','URGENT'),
    IN p_deadline DATE,
    OUT p_task_id INT
)
BEGIN
    INSERT INTO tasks (milestone_id, assignee_id, name, description, priority, deadline)
    VALUES (p_milestone_id, p_assignee_id, p_name, p_description, p_priority, p_deadline);
    SET p_task_id = LAST_INSERT_ID();
END;

DROP PROCEDURE IF EXISTS sp_update_task_status;
CREATE PROCEDURE sp_update_task_status(
    IN p_task_id INT,
    IN p_new_status ENUM('TODO','IN_PROGRESS','COMPLETED','CANCELLED'),
    IN p_action VARCHAR(100)
)
BEGIN
    DECLARE v_current_status VARCHAR(30);

    SELECT status INTO v_current_status FROM tasks WHERE id = p_task_id;
    IF v_current_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Task not found';
    END IF;

    IF v_current_status = p_new_status THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Task already in target status';
    END IF;

    IF v_current_status IN ('COMPLETED','CANCELLED') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot change status of terminal task';
    END IF;

    UPDATE tasks SET status = p_new_status WHERE id = p_task_id;
END;

DROP PROCEDURE IF EXISTS sp_complete_task;
CREATE PROCEDURE sp_complete_task(IN p_task_id INT)
BEGIN
    CALL sp_update_task_status(p_task_id, 'COMPLETED', 'complete');
END;

-- READ Operations

DROP PROCEDURE IF EXISTS sp_get_user_by_id;
CREATE PROCEDURE sp_get_user_by_id(IN p_user_id INT)
BEGIN
    SELECT id, username, email, preferences, created_at
    FROM users
    WHERE id = p_user_id;
END;

DROP PROCEDURE IF EXISTS sp_get_user_by_credentials;
CREATE PROCEDURE sp_get_user_by_credentials(IN p_username_or_email VARCHAR(150))
BEGIN
    SELECT id, username, email, password_hash, preferences, created_at
    FROM users
    WHERE username = p_username_or_email OR email = p_username_or_email;
END;

DROP PROCEDURE IF EXISTS sp_get_project_by_id;
CREATE PROCEDURE sp_get_project_by_id(IN p_project_id INT)
BEGIN
    SELECT id, name, description, start_date, deadline, status, created_at, updated_at
    FROM projects
    WHERE id = p_project_id;
END;

DROP PROCEDURE IF EXISTS sp_list_projects;
CREATE PROCEDURE sp_list_projects()
BEGIN
    SELECT id, name, description, start_date, deadline, status, created_at, updated_at
    FROM projects
    ORDER BY id;
END;

DROP PROCEDURE IF EXISTS sp_get_milestone_by_id;
CREATE PROCEDURE sp_get_milestone_by_id(IN p_milestone_id INT)
BEGIN
    SELECT id, project_id, name, description, deadline, status, created_at, updated_at
    FROM milestones
    WHERE id = p_milestone_id;
END;

DROP PROCEDURE IF EXISTS sp_list_milestones;
CREATE PROCEDURE sp_list_milestones(IN p_project_id INT)
BEGIN
    SELECT id, project_id, name, description, deadline, status, created_at, updated_at
    FROM milestones
    WHERE p_project_id IS NULL OR project_id = p_project_id
    ORDER BY id;
END;

DROP PROCEDURE IF EXISTS sp_get_task_by_id;
CREATE PROCEDURE sp_get_task_by_id(IN p_task_id INT)
BEGIN
    SELECT id, milestone_id, assignee_id, name, description, priority, status, deadline, created_at, updated_at
    FROM tasks
    WHERE id = p_task_id;
END;

DROP PROCEDURE IF EXISTS sp_list_tasks;
CREATE PROCEDURE sp_list_tasks(
    IN p_milestone_id INT,
    IN p_assignee_id INT,
    IN p_status VARCHAR(30)
)
BEGIN
    SELECT id, milestone_id, assignee_id, name, description, priority, status, deadline, created_at, updated_at
    FROM tasks
    WHERE (p_milestone_id IS NULL OR milestone_id = p_milestone_id)
      AND (p_assignee_id IS NULL OR assignee_id = p_assignee_id)
      AND (p_status IS NULL OR status = p_status)
    ORDER BY id;
END;

-- REPORT Operations (moved to functions.sql)

-- UPDATE Operations

DROP PROCEDURE IF EXISTS sp_update_project;
CREATE PROCEDURE sp_update_project(
    IN p_project_id INT,
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_start_date DATE,
    IN p_deadline DATE,
    IN p_status ENUM('PLANNED','ACTIVE','COMPLETED','CANCELLED')
)
BEGIN
    UPDATE projects
    SET name = p_name,
        description = p_description,
        start_date = p_start_date,
        deadline = p_deadline,
        status = p_status
    WHERE id = p_project_id;
END;

DROP PROCEDURE IF EXISTS sp_update_milestone;
CREATE PROCEDURE sp_update_milestone(
    IN p_milestone_id INT,
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_deadline DATE,
    IN p_status ENUM('PENDING','IN_PROGRESS','COMPLETED')
)
BEGIN
    UPDATE milestones
    SET name = p_name,
        description = p_description,
        deadline = p_deadline,
        status = p_status
    WHERE id = p_milestone_id;
END;

DROP PROCEDURE IF EXISTS sp_update_task;
CREATE PROCEDURE sp_update_task(
    IN p_task_id INT,
    IN p_milestone_id INT,
    IN p_assignee_id INT,
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_priority ENUM('LOW','MEDIUM','HIGH','URGENT'),
    IN p_deadline DATE,
    IN p_status ENUM('TODO','IN_PROGRESS','COMPLETED','CANCELLED')
)
BEGIN
    UPDATE tasks
    SET milestone_id = p_milestone_id,
        assignee_id = p_assignee_id,
        name = p_name,
        description = p_description,
        priority = p_priority,
        deadline = p_deadline,
        status = p_status
    WHERE id = p_task_id;
END;

-- DELETE Operations

DROP PROCEDURE IF EXISTS sp_delete_project;
CREATE PROCEDURE sp_delete_project(IN p_project_id INT)
BEGIN
    DELETE FROM projects WHERE id = p_project_id;
END;

DROP PROCEDURE IF EXISTS sp_delete_milestone;
CREATE PROCEDURE sp_delete_milestone(IN p_milestone_id INT)
BEGIN
    DELETE FROM milestones WHERE id = p_milestone_id;
END;

DROP PROCEDURE IF EXISTS sp_delete_task;
CREATE PROCEDURE sp_delete_task(IN p_task_id INT)
BEGIN
    DELETE FROM tasks WHERE id = p_task_id;
END;

-- USER Operations

DROP PROCEDURE IF EXISTS sp_update_user_preferences;
CREATE PROCEDURE sp_update_user_preferences(IN p_user_id INT, IN p_preferences JSON)
BEGIN
    UPDATE users SET preferences = p_preferences WHERE id = p_user_id;
END;