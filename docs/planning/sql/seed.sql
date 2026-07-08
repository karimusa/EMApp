-- MonthEndOrchestrationDB seed data
-- Run AFTER docs/planning/sql/schema.sql
--
-- Edit the variables below for your environment, then execute in SSMS or sqlcmd.
-- Application code does not hardcode these values — they live in the database.

SET NOCOUNT ON;

-- === Edit connection targets before running ===
DECLARE @PrimaryServer   NVARCHAR(200) = N'YOUR_PRIMARY_SERVER';
DECLARE @PrimaryDatabase NVARCHAR(200) = N'YOUR_ORCHESTRATION_DATABASE';
DECLARE @PrimaryUser     NVARCHAR(200) = N'YOUR_PRIMARY_USER';
DECLARE @PrimaryPassword NVARCHAR(200) = N'YOUR_PRIMARY_PASSWORD';

DECLARE @RemoteServer    NVARCHAR(200) = N'YOUR_REMOTE_SERVER';
DECLARE @RemoteDatabase  NVARCHAR(200) = N'msdb';
DECLARE @RemoteUser      NVARCHAR(200) = N'YOUR_REMOTE_USER';
DECLARE @RemotePassword  NVARCHAR(200) = N'YOUR_REMOTE_PASSWORD';
-- =============================================

-- Users: set password hashes with scripts/encrypt_password.py or seed_database.py
-- The Python seeder (scripts/seed_database.py) is the recommended path.

IF NOT EXISTS (SELECT 1 FROM orchestration.jobs WHERE job_id = 1)
BEGIN
    INSERT INTO orchestration.jobs (job_id, job_name, description, is_active)
    VALUES (1, N'RRA Month-End Orchestration', N'End-to-end month-end close orchestration.', 1);
END;

IF NOT EXISTS (SELECT 1 FROM orchestration.app_connections WHERE connection_name = N'PRIMARY')
BEGIN
    INSERT INTO orchestration.app_connections
        (connection_name, server_name, database_name, username, password_plain, is_active)
    VALUES (N'PRIMARY', @PrimaryServer, @PrimaryDatabase, @PrimaryUser, @PrimaryPassword, 1);
END;

IF NOT EXISTS (SELECT 1 FROM orchestration.app_connections WHERE connection_name = N'REMOTE_SQL')
BEGIN
    INSERT INTO orchestration.app_connections
        (connection_name, server_name, database_name, username, password_plain, is_active)
    VALUES (N'REMOTE_SQL', @RemoteServer, @RemoteDatabase, @RemoteUser, @RemotePassword, 1);
END;

IF NOT EXISTS (SELECT 1 FROM orchestration.job_runs WHERE run_id = 42)
BEGIN
    INSERT INTO orchestration.job_runs
        (run_id, job_id, period_label, status, started_at, started_by)
    VALUES (42, 1, N'May 2025', N'In Progress', '2025-05-31T02:15:00', N'admin');
END;

PRINT 'Base seed rows inserted.';
PRINT 'For full job_steps, step_runs, logs, and users run: python scripts/seed_database.py';
