-- MonthEndOrchestrationDB reference schema
-- Deploy on your SQL Server instance, then seed with scripts/seed_database.py

-- ============================================================
-- dbo.users — application authentication
-- ============================================================
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'users' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    CREATE TABLE dbo.users (
        user_id         INT IDENTITY(1,1) PRIMARY KEY,
        username        NVARCHAR(100) NOT NULL UNIQUE,
        password_hash   NVARCHAR(255) NOT NULL,
        role            NVARCHAR(20)  NOT NULL CHECK (role IN ('Admin', 'ReadOnly')),
        is_active       BIT NOT NULL DEFAULT 1,
        created_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at      DATETIME2 NULL
    );
END;
GO

-- ============================================================
-- orchestration.app_connections — dynamic connection registry
-- ============================================================
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'orchestration')
    EXEC('CREATE SCHEMA orchestration');
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'app_connections' AND schema_id = SCHEMA_ID('orchestration'))
BEGIN
    CREATE TABLE orchestration.app_connections (
        connection_id              INT IDENTITY(1,1) PRIMARY KEY,
        environment_name           NVARCHAR(50)  NOT NULL UNIQUE,  -- PRIMARY, REMOTE_SQL
        is_active                  BIT NOT NULL DEFAULT 1,
        server_name                NVARCHAR(200) NOT NULL,
        database_name              NVARCHAR(200) NOT NULL,
        auth_type                  NVARCHAR(50)  NOT NULL DEFAULT 'sql',
        sql_username               NVARCHAR(200) NULL,
        sql_password_hash          NVARCHAR(MAX) NULL,
        description                NVARCHAR(500) NULL,
        created_at                 DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at                 DATETIME2 NULL
    );
END;
GO

-- Seed connections via scripts/seed_database.py or docs/planning/sql/seed.sql

-- ============================================================
-- orchestration.job_steps — dashboard step definitions
-- ============================================================
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'job_steps' AND schema_id = SCHEMA_ID('orchestration'))
BEGIN
    CREATE TABLE orchestration.job_steps (
        step_id             INT IDENTITY(1,1) PRIMARY KEY,
        job_id              INT NOT NULL,
        step_name           NVARCHAR(200) NOT NULL,
        phase_code          NVARCHAR(20)  NOT NULL CHECK (phase_code IN ('PRE','MAIN','BI','DAY5','POST')),
        server_name         NVARCHAR(200) NOT NULL,
        step_order          INT NOT NULL DEFAULT 0,
        execute_proc_name   NVARCHAR(500) NOT NULL,
        validate_proc_name  NVARCHAR(500) NOT NULL,
        is_enabled          BIT NOT NULL DEFAULT 1
    );
END;
GO

-- Additional orchestration tables
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'jobs' AND schema_id = SCHEMA_ID('orchestration'))
BEGIN
    CREATE TABLE orchestration.jobs (
        job_id          INT IDENTITY(1,1) PRIMARY KEY,
        job_name        NVARCHAR(200) NOT NULL,
        description     NVARCHAR(500) NULL,
        is_active       BIT NOT NULL DEFAULT 1,
        created_at      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'job_runs' AND schema_id = SCHEMA_ID('orchestration'))
BEGIN
    CREATE TABLE orchestration.job_runs (
        run_id              INT IDENTITY(1,1) PRIMARY KEY,
        job_id              INT NOT NULL,
        period_label        NVARCHAR(50) NOT NULL,
        status              NVARCHAR(20) NOT NULL,
        started_at          DATETIME2 NOT NULL,
        completed_at        DATETIME2 NULL,
        duration_seconds    INT NULL,
        started_by          NVARCHAR(100) NOT NULL
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'step_runs' AND schema_id = SCHEMA_ID('orchestration'))
BEGIN
    CREATE TABLE orchestration.step_runs (
        step_run_id         INT IDENTITY(1,1) PRIMARY KEY,
        run_id              INT NOT NULL,
        step_id             INT NOT NULL,
        execution_status    NVARCHAR(20) NOT NULL,
        validation_status   NVARCHAR(20) NOT NULL,
        last_message        NVARCHAR(MAX) NULL,
        duration_seconds    INT NULL,
        started_at          DATETIME2 NULL,
        completed_at        DATETIME2 NULL,
        run_by              NVARCHAR(100) NULL
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'db_execution_log' AND schema_id = SCHEMA_ID('orchestration'))
BEGIN
    CREATE TABLE orchestration.db_execution_log (
        log_id              INT IDENTITY(1,1) PRIMARY KEY,
        run_id              INT NOT NULL,
        phase               NVARCHAR(20) NOT NULL,
        step_name           NVARCHAR(200) NOT NULL,
        message             NVARCHAR(MAX) NOT NULL,
        status              NVARCHAR(20) NOT NULL,
        duration_seconds    INT NULL,
        server_name         NVARCHAR(200) NOT NULL,
        logged_at           DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'run_metrics' AND schema_id = SCHEMA_ID('orchestration'))
BEGIN
    CREATE TABLE orchestration.run_metrics (
        metric_id                   INT IDENTITY(1,1) PRIMARY KEY,
        run_id                      INT NOT NULL,
        total_steps                 INT NOT NULL,
        success_count               INT NOT NULL,
        failed_count                INT NOT NULL,
        running_count               INT NOT NULL,
        pending_count               INT NOT NULL,
        validation_failed_count     INT NOT NULL,
        progress_pct                INT NOT NULL,
        updated_at                  DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'monitored_agent_jobs' AND schema_id = SCHEMA_ID('orchestration'))
BEGIN
    CREATE TABLE orchestration.monitored_agent_jobs (
        job_name        NVARCHAR(200) NOT NULL PRIMARY KEY,
        alt_name        NVARCHAR(200) NULL,
        environment_name NVARCHAR(50)  NOT NULL
    );
END;
GO
