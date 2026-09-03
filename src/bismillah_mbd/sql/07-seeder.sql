USE TaskManager;

-- Seed Users
INSERT INTO users (username, email, password_hash) VALUES
('john_doe', 'john@example.com', '$2y$10$dummyhash1'),
('jane_smith', 'jane@example.com', '$2y$10$dummyhash2'),
('bob_wilson', 'bob@example.com', '$2y$10$dummyhash3'),
('alice_jones', 'alice@example.com', '$2y$10$dummyhash4'),
('charlie_brown', 'charlie@example.com', '$2y$10$dummyhash5');

-- Seed Projects
INSERT INTO projects (name, description, start_date, deadline, status) VALUES
('Website Redesign', 'Complete redesign of company website', '2024-01-15', '2024-06-30', 'ACTIVE'),
('Mobile App Development', 'Build iOS and Android app', '2024-02-01', '2024-08-15', 'PLANNED'),
('API Integration', 'Integrate third-party payment API', '2024-03-01', '2024-05-31', 'ACTIVE'),
('Database Migration', 'Migrate from MySQL to PostgreSQL', '2024-01-10', '2024-04-15', 'COMPLETED'),
('Security Audit', 'Perform comprehensive security audit', '2024-04-01', '2024-07-01', 'PLANNED');

-- Seed Milestones
INSERT INTO milestones (project_id, name, description, deadline, status) VALUES
-- Website Redesign milestones
(1, 'Design Phase', 'Create wireframes and mockups', '2024-02-28', 'COMPLETED'),
(1, 'Frontend Development', 'Implement responsive frontend', '2024-04-30', 'IN_PROGRESS'),
(1, 'Backend Integration', 'Connect frontend to backend APIs', '2024-05-31', 'PENDING'),
(1, 'Testing & Launch', 'QA testing and production deployment', '2024-06-30', 'PENDING'),

-- Mobile App Development milestones
(2, 'Requirements Gathering', 'Define app features and user stories', '2024-03-15', 'PENDING'),
(2, 'UI/UX Design', 'Design app screens and user flows', '2024-04-30', 'PENDING'),
(2, 'iOS Development', 'Build native iOS application', '2024-07-01', 'PENDING'),
(2, 'Android Development', 'Build native Android application', '2024-07-15', 'PENDING'),
(2, 'App Store Deployment', 'Submit to App Store and Play Store', '2024-08-15', 'PENDING'),

-- API Integration milestones
(3, 'API Research', 'Evaluate payment providers', '2024-03-15', 'COMPLETED'),
(3, 'Sandbox Integration', 'Implement in test environment', '2024-04-30', 'IN_PROGRESS'),
(3, 'Production Integration', 'Deploy to production', '2024-05-31', 'PENDING'),

-- Database Migration milestones
(4, 'Schema Migration', 'Convert schema to PostgreSQL', '2024-02-15', 'COMPLETED'),
(4, 'Data Migration', 'Transfer all data', '2024-03-15', 'COMPLETED'),
(4, 'Testing & Cutover', 'Verify and switch production', '2024-04-15', 'COMPLETED'),

-- Security Audit milestones
(5, 'Planning', 'Define scope and methodology', '2024-04-15', 'PENDING'),
(5, 'Vulnerability Scanning', 'Automated and manual scans', '2024-05-31', 'PENDING'),
(5, 'Report & Remediation', 'Document findings and fixes', '2024-07-01', 'PENDING');

-- Seed Tasks
INSERT INTO tasks (assignee_id, milestone_id, name, description, priority, status, deadline) VALUES
-- Design Phase tasks (milestone 1)
(1, 1, 'Create wireframes', 'Design low-fidelity wireframes for all pages', 'HIGH', 'COMPLETED', '2024-02-10'),
(2, 1, 'Design system', 'Create component library and style guide', 'HIGH', 'COMPLETED', '2024-02-20'),
(3, 1, 'High-fidelity mockups', 'Create pixel-perfect designs', 'MEDIUM', 'COMPLETED', '2024-02-28'),

-- Frontend Development tasks (milestone 2)
(1, 2, 'Setup React project', 'Initialize project with TypeScript and tooling', 'HIGH', 'COMPLETED', '2024-03-15'),
(2, 2, 'Build header component', 'Responsive navigation with auth', 'MEDIUM', 'IN_PROGRESS', '2024-03-30'),
(3, 2, 'Build footer component', 'Site footer with links and social', 'LOW', 'TODO', '2024-04-05'),
(4, 2, 'Implement homepage', 'Hero, features, testimonials sections', 'HIGH', 'IN_PROGRESS', '2024-04-15'),
(5, 2, 'Implement dashboard', 'User dashboard with metrics', 'HIGH', 'TODO', '2024-04-30'),

-- Backend Integration tasks (milestone 3)
(1, 3, 'Auth API integration', 'Connect login/register flows', 'HIGH', 'TODO', '2024-05-10'),
(2, 3, 'Data fetching hooks', 'Create reusable data fetching hooks', 'MEDIUM', 'TODO', '2024-05-20'),
(3, 3, 'Error boundaries', 'Implement error handling UI', 'MEDIUM', 'TODO', '2024-05-25'),

-- Testing & Launch tasks (milestone 4)
(4, 4, 'E2E test setup', 'Configure Cypress for E2E testing', 'MEDIUM', 'TODO', '2024-06-10'),
(5, 4, 'Performance audit', 'Lighthouse and bundle analysis', 'HIGH', 'TODO', '2024-06-20'),
(1, 4, 'Production deployment', 'Deploy to Vercel/AWS', 'URGENT', 'TODO', '2024-06-30'),

-- Mobile App - Requirements (milestone 5)
(1, 5, 'User research', 'Interview 10 target users', 'HIGH', 'TODO', '2024-03-01'),
(2, 5, 'Competitive analysis', 'Analyze 5 competitor apps', 'MEDIUM', 'TODO', '2024-03-10'),
(3, 5, 'Feature prioritization', 'MoSCoW prioritization workshop', 'HIGH', 'TODO', '2024-03-15'),

-- API Integration - Sandbox (milestone 12)
(4, 12, 'Stripe sandbox setup', 'Configure test webhooks', 'HIGH', 'IN_PROGRESS', '2024-04-10'),
(5, 12, 'Payment flow implementation', 'Checkout and subscription flows', 'URGENT', 'TODO', '2024-04-25'),
(1, 12, 'Webhook handling', 'Process payment events', 'HIGH', 'TODO', '2024-04-30'),

-- Security Audit - Planning (milestone 15)
(2, 15, 'Scope definition', 'Define systems in scope', 'HIGH', 'TODO', '2024-04-10'),
(3, 15, 'Tool selection', 'Choose scanning tools', 'MEDIUM', 'TODO', '2024-04-15');

-- Seed Activity Logs
INSERT INTO activity_logs (task_id, action, old_status, new_status) VALUES
(1, 'status_change', 'TODO', 'IN_PROGRESS'),
(1, 'status_change', 'IN_PROGRESS', 'COMPLETED'),
(2, 'status_change', 'TODO', 'IN_PROGRESS'),
(2, 'status_change', 'IN_PROGRESS', 'COMPLETED'),
(4, 'status_change', 'TODO', 'IN_PROGRESS'),
(5, 'status_change', 'TODO', 'IN_PROGRESS'),
(12, 'status_change', 'TODO', 'IN_PROGRESS'),
(13, 'status_change', 'TODO', 'IN_PROGRESS');