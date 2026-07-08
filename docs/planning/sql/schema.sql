-- MonthEndOrchestrationDB reference schema
-- Source of truth: MonthEndOrchestrationDB on SPUS001BDBEXT

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
        connection_name            NVARCHAR(50)  NOT NULL UNIQUE,  -- PRIMARY, REMOTE_SQL
        server_name                NVARCHAR(200) NOT NULL,
        database_name              NVARCHAR(200) NOT NULL,
        username                   NVARCHAR(200) NOT NULL,
        password_encrypted         NVARCHAR(MAX) NULL,  -- Fernet-encrypted; NOT a login hash
        password_plain               NVARCHAR(200) NULL,  -- avoid in production; dev only
        driver                     NVARCHAR(200) NULL DEFAULT 'ODBC Driver 18 for SQL Server',
        trust_server_certificate   NVARCHAR(10)  NULL DEFAULT 'yes',
        is_active                  BIT NOT NULL DEFAULT 1,
        created_at                 DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at                 DATETIME2 NULL
    );
END;
GO

-- Seed connections (encrypt passwords via app utility before production use)
-- PRIMARY  -> SPUS001BDBEXT -> MonthEndOrchestrationDB
-- REMOTE_SQL -> SPAZ001EDM10 -> msdb

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

-- Additional tables: jobs, job_runs, step_runs, db_execution_log, run_metrics
-- See docs/sql/stored_procedures.sql for execution/validation proc contracts.
