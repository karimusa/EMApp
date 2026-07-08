"""Frozen proc-mapping registry — static contract mirrored in orchestration.job_steps."""

from __future__ import annotations

import re
from typing import NamedTuple


class StepDef(NamedTuple):
    phase_code: str
    step_name: str
    connection_name: str
    execute_proc: str
    validate_proc: str
    agent_job: str | None = None


PHASES: list[dict[str, str]] = [
    {"key": "PRE", "label": "PRE"},
    {"key": "MAIN", "label": "MAIN"},
    {"key": "BI", "label": "BI"},
    {"key": "DAY5", "label": "DAY 5"},
    {"key": "POST", "label": "POST"},
]

STEP_REGISTRY: list[StepDef] = [
    StepDef("PRE", "Send Start Email", "PRIMARY",
            "orchestration.sp_send_month_end_start_email",
            "orchestration.sp_validate_month_end_start_email"),
    StepDef("PRE", "Backup BI DB", "PRIMARY", "usp_backup_bi", "usp_validate_backup_bi"),
    StepDef("PRE", "Backup RRAPS DB", "PRIMARY", "usp_backup_RRAPS", "usp_validate_backup_RRAPS"),
    StepDef("PRE", "Backup Warehouse DB", "PRIMARY",
            "usp_backup_warehouse", "usp_validate_backup_warehouse"),
    StepDef("MAIN", "Populate KeyClient", "PRIMARY",
            "usp_me_01_populate_keyclient", "usp_validate_me_01_populate_keyclient"),
    StepDef("MAIN", "Backup BigFish Tables", "PRIMARY",
            "usp_me_02_backup_bigfish_tables", "usp_validate_me_02_backup_bigfish_tables"),
    StepDef("MAIN", "Run BigFish Load Job", "PRIMARY",
            "usp_me_03_run_bigfish_job", "usp_validate_me_03_run_bigfish_job",
            "zz-Load Big Fish Dashboard Data 2016"),
    StepDef("MAIN", "Populate BigFish Tables", "PRIMARY",
            "usp_me_04_populate_bigfish_tables", "usp_validate_me_04_populate_bigfish_tables"),
    StepDef("MAIN", "Validate BigFish Dashboard", "PRIMARY",
            "usp_me_05_validate_bigfish_dashboard",
            "usp_validate_me_05_validate_bigfish_dashboard"),
    StepDef("MAIN", "Populate Quadrant Tables", "PRIMARY",
            "usp_me_06_populate_quadrant_tables", "usp_validate_me_06_populate_quadrant_tables"),
    StepDef("MAIN", "Run Azure Job", "REMOTE_SQL",
            "usp_me_07_run_azure_pshr_job", "usp_validate_me_07_run_azure_pshr_job",
            "Azure_PSHRDataLoads"),
    StepDef("MAIN", "Run CompTaskForce Job", "PRIMARY",
            "usp_me_08_run_comptaskforce_job", "usp_validate_me_08_run_comptaskforce_job",
            "zz_Load CompTaskForce Data 2016"),
    StepDef("MAIN", "Fix Employee Role Data", "PRIMARY",
            "usp_me_09_fix_employee_role_data", "usp_validate_me_09_fix_employee_role_data"),
    StepDef("MAIN", "Validate Measurement Dashboard", "PRIMARY",
            "usp_me_10_validate_measurement_dashboard",
            "usp_validate_me_10_validate_measurement_dashboard"),
    StepDef("BI", "Insert AsOfDate", "PRIMARY",
            "usp_me_11_insert_asofdate_rraps", "usp_validate_me_11_insert_asofdate_rraps"),
    StepDef("BI", "Load PeopleSoft Revenue", "PRIMARY",
            "usp_me_12_load_peoplesoft_revenue", "usp_validate_me_12_load_peoplesoft_revenue"),
    StepDef("BI", "Load WIP Tables", "PRIMARY",
            "usp_me_13_load_wip_tables", "usp_validate_me_13_load_wip_tables"),
    StepDef("BI", "Check Consultant Workload", "PRIMARY",
            "usp_me_14_check_and_load_consultant_workload",
            "usp_validate_me_14_check_and_load_consultant_workload",
            "RRAPS_Populate Consultant_workload table - Monthly Load"),
    StepDef("BI", "Run OfficeFull Model", "PRIMARY",
            "usp_me_15_run_officefull_model", "usp_validate_me_15_run_officefull_model"),
    StepDef("BI", "Run BI Finance Job", "PRIMARY",
            "usp_me_16_run_bi_finance_job", "usp_validate_me_16_run_bi_finance_job",
            "BI_FINANCE_DATA"),
    StepDef("BI", "Check Employee Role Data", "PRIMARY",
            "usp_me_17_check_employee_role_data", "usp_validate_me_17_check_employee_role_data"),
    StepDef("BI", "Consultant Quadrant Data Load", "PRIMARY",
            "usp_me_18_consultant_quadrant_data_load",
            "usp_validate_me_18_consultant_quadrant_data_load"),
    StepDef("BI", "Area Manager Dashboard Load", "PRIMARY",
            "usp_me_19_area_manager_dashboard_load",
            "usp_validate_me_19_area_manager_dashboard_load"),
    StepDef("BI", "Insert Historical Tables", "PRIMARY",
            "usp_me_20_insert_historical_tables", "usp_validate_me_20_insert_historical_tables"),
    StepDef("DAY5", "Refresh PeopleSoft Revenue", "PRIMARY",
            "usp_me_d5_01_refresh_peoplesoft_revenue",
            "usp_validate_me_d5_01_refresh_peoplesoft_revenue"),
    StepDef("DAY5", "Run OfficeFull Model", "PRIMARY",
            "usp_me_d5_02_run_officefull_model", "usp_validate_me_d5_02_run_officefull_model"),
    StepDef("POST", "Send Complete Email", "PRIMARY",
            "orchestration.sp_send_month_end_complete_email",
            "orchestration.sp_validate_month_end_complete_email"),
]

_AGENT_BY_PROC = {s.execute_proc: s.agent_job for s in STEP_REGISTRY if s.agent_job}
_TRIGGER_BY_JOB = {
    s.agent_job: {"step_name": s.step_name, "execute_proc": s.execute_proc}
    for s in STEP_REGISTRY
    if s.agent_job
}


def job_key(job_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", job_name.lower()).strip("-")


def agent_job_for_proc(execute_proc: str) -> str | None:
    return _AGENT_BY_PROC.get(execute_proc)


def trigger_for_job(job_name: str) -> dict[str, str | None]:
    return _TRIGGER_BY_JOB.get(job_name, {})
