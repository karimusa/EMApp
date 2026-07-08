-- Add decryptable SQL credential column for orchestration.app_connections.
-- Run once on existing MonthEndOrchestrationDB deployments.
--
-- sql_password_hash was a misleading legacy name. Do NOT store SHA/bcrypt hashes
-- there for runtime SQL authentication. Use sql_password_encrypted instead.

SET NOCOUNT ON;

IF COL_LENGTH('orchestration.app_connections', 'sql_password_encrypted') IS NULL
BEGIN
    ALTER TABLE orchestration.app_connections
        ADD sql_password_encrypted NVARCHAR(MAX) NULL;
END;
GO

-- Optional: move plain-text legacy values forward (skip one-way hashes).
UPDATE orchestration.app_connections
SET sql_password_encrypted = sql_password_hash,
    sql_password_hash = NULL,
    updated_at = SYSUTCDATETIME()
WHERE sql_password_encrypted IS NULL
  AND sql_password_hash IS NOT NULL
  AND LEN(sql_password_hash) <> 64
  AND sql_password_hash NOT LIKE 'pbkdf2:%'
  AND sql_password_hash NOT LIKE 'scrypt:%'
  AND sql_password_hash NOT LIKE '$2%'
  AND sql_password_hash NOT LIKE 'gAAAAA%';
GO

PRINT 'sql_password_encrypted column is ready.';
