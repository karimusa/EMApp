-- Stored procedure contracts for RRA Month-End Orchestration
-- Validation is procedure-based (not table-based).

-- ============================================================
-- orchestration.usp_GetMonitoredAgentJobs
-- Returns monitored SQL Agent jobs for the UI in one result set.
-- Deploy on each connection database that hosts monitored SQL Agent jobs.
-- Server names come from orchestration.app_connections at runtime.
-- ============================================================
CREATE OR ALTER PROCEDURE orchestration.usp_GetMonitoredAgentJobs
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        j.name                          AS job_name,
        j.enabled                       AS is_enabled,
        CASE h.run_status
            WHEN 0 THEN 'Failed'
            WHEN 1 THEN 'Succeeded'
            WHEN 2 THEN 'Retry'
            WHEN 3 THEN 'Canceled'
            WHEN 4 THEN 'Running'
            ELSE 'Unknown'
        END                             AS last_run_status,
        h.run_date                      AS last_run_time,
        ja.next_scheduled_run_date      AS next_run_time,
        CASE WHEN ja.start_execution_date IS NOT NULL
                  AND ja.stop_execution_date IS NULL THEN 1 ELSE 0 END AS is_running
    FROM msdb.dbo.sysjobs j
    INNER JOIN orchestration.monitored_agent_jobs m ON m.job_name = j.name
    OUTER APPLY (
        SELECT TOP 1 h.run_status, h.run_date
        FROM msdb.dbo.sysjobhistory h
        WHERE h.job_id = j.job_id AND h.step_id = 0
        ORDER BY h.run_date DESC
    ) h
    OUTER APPLY (
        SELECT TOP 1 start_execution_date, stop_execution_date, next_scheduled_run_date
        FROM msdb.dbo.sysjobactivity
        WHERE job_id = j.job_id
        ORDER BY session_id DESC
    ) ja
    ORDER BY j.name;
END;
GO

-- ============================================================
-- Example validation procedure contract
-- Each step has orchestration.usp_Validate_<StepName>
-- Returns a single UI-friendly row:
-- ============================================================
-- CREATE OR ALTER PROCEDURE orchestration.usp_Validate_GLPosting
--     @step_id       INT,
--     @validated_by  NVARCHAR(100)
-- AS
-- BEGIN
--     SELECT
--         'GL Posting'           AS step_name,
--         'Completed'            AS latest_log_status,
--         '12450'                AS expected_item,
--         'row_count'            AS matched_item_type,
--         'PASS'                 AS pass_fail,
--         'Row count matches expected.' AS result_message,
--         SYSUTCDATETIME()       AS validation_time;
-- END;

-- ============================================================
-- Example execution procedure contract
-- ============================================================
-- CREATE OR ALTER PROCEDURE orchestration.usp_Execute_GLPosting
--     @step_id  INT,
--     @run_by   NVARCHAR(100)
-- AS
-- BEGIN
--     -- Execute one step; log to orchestration.db_execution_log
--     -- Update orchestration.step_runs
--     SELECT
--         CAST(1 AS BIT)         AS success,
--         'GL posting completed.' AS message,
--         'Completed'            AS execution_status;
-- END;
