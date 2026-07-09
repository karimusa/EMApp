-- Add logical connection target to orchestration.job_steps.
-- Runtime host/database values remain in orchestration.app_connections.

IF COL_LENGTH('orchestration.job_steps', 'environment_name') IS NULL
BEGIN
    ALTER TABLE orchestration.job_steps
        ADD environment_name NVARCHAR(50) NULL;
END;
GO

UPDATE js
SET js.environment_name = CASE
    WHEN js.server_name IN (
        SELECT server_name FROM orchestration.app_connections WHERE environment_name = N'REMOTE_SQL'
    ) THEN N'REMOTE_SQL'
    ELSE N'PRIMARY'
END
FROM orchestration.job_steps js
WHERE js.environment_name IS NULL OR LTRIM(RTRIM(js.environment_name)) = N'';
GO
