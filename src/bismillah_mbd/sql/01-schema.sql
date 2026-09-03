CREATE DATABASE IF NOT EXISTS TaskManager;

USE TaskManager;

CREATE TABLE projects (
    id int AUTO_INCREMENT PRIMARY KEY,
    name varchar(150) NOT NULL,
    description text,
    start_date date NOT NULL,
    deadline date NOT NULL,
    status ENUM(
        'PLANNED',
        'ACTIVE',
        'COMPLETED',
        'CANCELLED'
        ) NOT NULL DEFAULT 'PLANNED',
    created_at timestamp NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp NOT NULL  DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT check_p_dates
                      CHECK ( deadline >= start_date )
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,

    username varchar(50) NOT NULL UNIQUE,
    email varchar(150) NOT NULL UNIQUE,
    password_hash varchar(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE milestones (
    id int AUTO_INCREMENT PRIMARY KEY,
    project_id int NOT NULL,
    name varchar(150) NOT NULL,
    description text,
    deadline date NOT NULL,
    status ENUM(
        'PENDING',
        'IN_PROGRESS',
        'COMPLETED'
        ) NOT NULL DEFAULT 'PENDING',
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_mil_pro
                        FOREIGN KEY (project_id)
                        REFERENCES projects(id)
                        ON DELETE CASCADE
);

CREATE TABLE tasks (
    id int AUTO_INCREMENT PRIMARY KEY,
    assignee_id int,
    milestone_id INT NOT NULL,
    name varchar(150) NOT NULL,
    description text,
    priority ENUM(
        'LOW',
        'MEDIUM',
        'HIGH',
        'URGENT'
        ) NOT NULL DEFAULT 'LOW',
    status ENUM(
        'TODO',
        'IN_PROGRESS',
        'COMPLETED',
        'CANCELLED'
        ) NOT NULL DEFAULT 'TODO',
    deadline date NOT NULL ,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_task_mil
                  FOREIGN KEY  (milestone_id)
                  REFERENCES milestones(id)
                  ON DELETE CASCADE,

    CONSTRAINT fk_task_assign
                FOREIGN KEY (assignee_id)
                REFERENCES users(id)
                ON DELETE SET NULL
);

CREATE TABLE activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id int NOT NULL,
    action VARCHAR(100) NOT NULL,

    old_status varchar(30),
    new_status varchar(30),

    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_act_task
                           FOREIGN KEY (task_id)
                           REFERENCES tasks(id)
                           ON DELETE CASCADE
);