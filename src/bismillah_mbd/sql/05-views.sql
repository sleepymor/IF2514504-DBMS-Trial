USE TaskManager;


-- Consumed by: GET /projects/
CREATE OR REPLACE VIEW v_projects AS
SELECT id,
       p.name,
       p.description,
       p.start_date,
       p.deadline,
       p.status,
       p.created_at,
       p.updated_at
FROM projects p
ORDER BY id;

-- Consumed by: GET /reports/tasks/overdue
CREATE OR REPLACE VIEW v_overdue_tasks AS
SELECT t.id AS task_id,
       t.name AS task_name,
       t.status,
       t.deadline,
       t.priority,
       t.milestone_id,
       m.name AS milestone_name,
       m.project_id,
       p.name AS project_name,
       t.assignee_id
FROM tasks t
JOIN milestones m ON t.milestone_id = m.id
JOIN projects p ON m.project_id = p.id
WHERE t.deadline < CURDATE()
  AND t.status NOT IN ('COMPLETED', 'CANCELLED')
ORDER BY t.deadline;

-- Consumed by: GET /reports/workload
CREATE OR REPLACE VIEW v_assignee_workload AS
SELECT u.id AS assignee_id,
       u.username AS assignee_username,
       u.email AS assignee_email,
       COUNT(t.id) AS open_task_count,
       SUM(IF (t.deadline < CURDATE() AND t.status NOT IN ('COMPLETED', 'CANCELLED'), 1, 0)) AS overdue_task_count
FROM users u
JOIN tasks t ON u.id = t.assignee_id
WHERE t.status NOT IN ('COMPLETED', 'CANCELLED')
GROUP BY u.id, u.username, u.email
HAVING open_task_count > 0
ORDER BY u.id;