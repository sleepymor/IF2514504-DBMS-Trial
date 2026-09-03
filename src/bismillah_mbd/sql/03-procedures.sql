USE TaskManager;

DELIMITER //

-- CREATE Operations

-- Consumed by: POST /auth/register
DROP PROCEDURE IF EXISTS sp_create_user;
CREATE PROCEDURE sp_create_user(
    IN p_username VARCHAR(50),
    IN p_email VARCHAR(150),
    IN p_password_hash VARCHAR(255),
    OUT p_user_id INT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO users (username, email, password_hash)
    VALUES (p_username, p_email, p_password_hash);
    SET p_user_id = LAST_INSERT_ID();
    COMMIT;
END//

-- Consumed by: POST /projects/
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
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO projects (name, description, start_date, deadline, status)
    VALUES (p_name, p_description, p_start_date, p_deadline, p_status);
    SET p_project_id = LAST_INSERT_ID();
    COMMIT;
END//

-- Consumed by: POST /projects/with-milestone
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
END//

-- Consumed by: POST /milestones/
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
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO milestones (project_id, name, description, deadline, status)
    VALUES (p_project_id, p_name, p_description, p_deadline, p_status);
    SET p_milestone_id = LAST_INSERT_ID();
    COMMIT;
END//

-- Consumed by: POST /tasks/
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
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    INSERT INTO tasks (milestone_id, assignee_id, name, description, priority, deadline)
    VALUES (p_milestone_id, p_assignee_id, p_name, p_description, p_priority, p_deadline);
    SET p_task_id = LAST_INSERT_ID();
    COMMIT;
END//

-- Consumed by: POST /tasks/{task_id}/start, POST /tasks/{task_id}/cancel
DROP PROCEDURE IF EXISTS sp_update_task_status;
CREATE PROCEDURE sp_update_task_status(
    IN p_task_id INT,
    IN p_new_status ENUM('TODO','IN_PROGRESS','COMPLETED','CANCELLED'),
    IN p_action VARCHAR(100)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
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
    COMMIT;
END//

-- Consumed by: POST /tasks/{task_id}/complete
DROP PROCEDURE IF EXISTS sp_complete_task;
CREATE PROCEDURE sp_complete_task(IN p_task_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    CALL sp_update_task_status(p_task_id, 'COMPLETED', 'complete');
END//

-- READ Operationsupdate

-- Consumed by: GET /users/{user_id}
DROP PROCEDURE IF EXISTS sp_get_user_by_id;
CREATE PROCEDURE sp_get_user_by_id(IN p_user_id INT)
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
BEGIN
    SELECT id, username, email, created_at
    FROM users
    WHERE id = p_user_id;
    COMMIT;
END//

-- Consumed by: POST /auth/login
DROP PROCEDURE IF EXISTS sp_get_user_by_credentials;
CREATE PROCEDURE sp_get_user_by_credentials(IN p_username_or_email VARCHAR(150))
BEGIN
    SELECT id, username, email, password_hash, created_at
    FROM users
    WHERE username = p_username_or_email OR email = p_username_or_email;
END//

-- Consumed by: GET /projects/{project_id}
DROP PROCEDURE IF EXISTS sp_get_project_by_id;
CREATE PROCEDURE sp_get_project_by_id(IN p_project_id INT)
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
BEGIN
    SELECT id, name, description, start_date, deadline, status, created_at, updated_at
    FROM projects
    WHERE id = p_project_id;
    
    SELECT id, project_id, name, description, deadline, status, created_at, updated_at
    FROM milestones
    WHERE project_id = p_project_id
    ORDER BY id;
    COMMIT;
END//

-- Consumed by: GET /milestones/{milestone_id}
DROP PROCEDURE IF EXISTS sp_get_milestone_by_id;
CREATE PROCEDURE sp_get_milestone_by_id(IN p_milestone_id INT)
BEGIN
    SELECT id, project_id, name, description, deadline, status, created_at, updated_at
    FROM milestones
    WHERE id = p_milestone_id;
    
    SELECT id, milestone_id, assignee_id, name, description, priority, status, deadline, created_at, updated_at
    FROM tasks
    WHERE milestone_id = p_milestone_id
    ORDER BY id;
END//

-- Consumed by: GET /milestones/
DROP PROCEDURE IF EXISTS sp_list_milestones;
CREATE PROCEDURE sp_list_milestones(IN p_project_id INT)
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
BEGIN
    SELECT id, project_id, name, description, deadline, status, created_at, updated_at
    FROM milestones
    WHERE p_project_id IS NULL OR project_id = p_project_id
    ORDER BY id;
    COMMIT;
END//

-- Consumed by: GET /tasks/{task_id}
DROP PROCEDURE IF EXISTS sp_get_task_by_id;
CREATE PROCEDURE sp_get_task_by_id(IN p_task_id INT)
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
BEGIN
    SELECT id, milestone_id, assignee_id, name, description, priority, status, deadline, created_at, updated_at
    FROM tasks
    WHERE id = p_task_id;
    COMMIT;
END//

-- Consumed by: GET /tasks/
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
END//

-- UPDATE Operations

-- Consumed by: PUT /projects/{project_id}
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
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    UPDATE projects
    SET name = p_name,
        description = p_description,
        start_date = p_start_date,
        deadline = p_deadline,
        status = p_status
    WHERE id = p_project_id;
    COMMIT;
END//

-- Consumed by: PUT /milestones/{milestone_id}
DROP PROCEDURE IF EXISTS sp_update_milestone;
CREATE PROCEDURE sp_update_milestone(
    IN p_milestone_id INT,
    IN p_name VARCHAR(150),
    IN p_description TEXT,
    IN p_deadline DATE,
    IN p_status ENUM('PENDING','IN_PROGRESS','COMPLETED')
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    UPDATE milestones
    SET name = p_name,
        description = p_description,
        deadline = p_deadline,
        status = p_status
    WHERE id = p_milestone_id;
    COMMIT;
END//

-- Consumed by: PUT /tasks/{task_id}
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
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    UPDATE tasks
    SET milestone_id = p_milestone_id,
        assignee_id = p_assignee_id,
        name = p_name,
        description = p_description,
        priority = p_priority,
        deadline = p_deadline,
        status = p_status
    WHERE id = p_task_id;
    COMMIT;
END//

-- DELETE Operations

-- Consumed by: DELETE /projects/{project_id}
DROP PROCEDURE IF EXISTS sp_delete_project;
CREATE PROCEDURE sp_delete_project(IN p_project_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    DELETE FROM projects WHERE id = p_project_id;
    COMMIT;
END//

-- Consumed by: DELETE /milestones/{milestone_id}
DROP PROCEDURE IF EXISTS sp_delete_milestone;
CREATE PROCEDURE sp_delete_milestone(IN p_milestone_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    DELETE FROM milestones WHERE id = p_milestone_id;
    COMMIT;
END//

-- Consumed by: DELETE /tasks/{task_id}
DROP PROCEDURE IF EXISTS sp_delete_task;
CREATE PROCEDURE sp_delete_task(IN p_task_id INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    DELETE FROM tasks WHERE id = p_task_id;
    COMMIT;
END//

DELIMITER ;