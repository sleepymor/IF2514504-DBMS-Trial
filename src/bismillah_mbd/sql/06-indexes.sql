USE TaskManager;

-- Secondary Indexes (B+Tree) for Query Optimization
-- Created after schema, functions, procedures, triggers, and views
-- Based on actual query patterns from API endpoints

-- ============================================================
-- TASKS TABLE INDEXES
-- ============================================================

-- Index for filtering tasks by assignee (GET /tasks/?assignee_id=X)
-- Used by: sp_list_tasks, v_tasks view
CREATE INDEX idx_tasks_assignee_id ON tasks (assignee_id);

-- Index for filtering tasks by milestone (GET /tasks/?milestone_id=X)
-- Used by: sp_list_tasks, v_tasks view, fn_get_milestone_progress
CREATE INDEX idx_tasks_milestone_id ON tasks (milestone_id);

-- Index for filtering tasks by status (GET /tasks/?status=X)
-- Used by: sp_list_tasks, v_tasks view, sp_update_task_status
CREATE INDEX idx_tasks_status ON tasks (status);

-- Index for deadline-based queries (GET /reports/tasks/overdue, deadline ordering)
-- Used by: v_overdue_tasks view, overdue reports
CREATE INDEX idx_tasks_deadline ON tasks (deadline);

-- Composite index for milestone + status filtering (common pattern)
-- Used by: project/milestone progress calculations
CREATE INDEX idx_tasks_milestone_status ON tasks (milestone_id, status);

-- Composite index for assignee + status filtering (workload queries)
-- Used by: v_assignee_workload view
CREATE INDEX idx_tasks_assignee_status ON tasks (assignee_id, status);

-- Composite index for deadline + status (overdue task queries)
-- Used by: v_overdue_tasks, v_assignee_workload
CREATE INDEX idx_tasks_deadline_status ON tasks (deadline, status);

-- ============================================================
-- MILESTONES TABLE INDEXES
-- ============================================================

-- Index for filtering milestones by project (GET /milestones/?project_id=X)
-- Used by: sp_list_milestones, v_milestones view
CREATE INDEX idx_milestones_project_id ON milestones (project_id);

-- Index for milestone status filtering
-- Used by: milestone status queries
CREATE INDEX idx_milestones_status ON milestones (status);

-- ============================================================
-- PROJECTS TABLE INDEXES
-- ============================================================

-- Index for project status filtering
-- Used by: project listing and filtering
CREATE INDEX idx_projects_status ON projects (status);

-- ============================================================
-- USERS TABLE INDEXES
-- ============================================================

-- Index for user lookup by username/email (authentication)
-- UNIQUE constraints already create implicit indexes on username and email
-- (See 01-schema.sql: UNIQUE on username, email)

-- ============================================================
-- ACTIVITY_LOGS TABLE INDEXES
-- ============================================================

-- Index for querying activity logs by task
-- Used by: task audit trail queries
CREATE INDEX idx_activity_logs_task_id ON activity_logs (task_id);

-- Index for time-based activity log queries
CREATE INDEX idx_activity_logs_created_at ON activity_logs (created_at);