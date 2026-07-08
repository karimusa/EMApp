#!/usr/bin/env python3
"""Seed MonthEndOrchestrationDB from the frozen STEP_REGISTRY and sample run data.

Reads connection target values from environment variables (not hardcoded in code).
Deploy schema.sql first, configure .env bootstrap credentials, then run:

  python scripts/seed_database.py

Environment (seed rows for orchestration.app_connections):
  SEED_PRIMARY_SERVER, SEED_PRIMARY_DATABASE, SEED_PRIMARY_USER, SEED_PRIMARY_PASSWORD
  SEED_REMOTE_SERVER,  SEED_REMOTE_DATABASE,  SEED_REMOTE_USER,  SEED_REMOTE_PASSWORD

Bootstrap (to reach the database):
  BOOTSTRAP_SERVER, BOOTSTRAP_DATABASE, BOOTSTRAP_USER, BOOTSTRAP_PASSWORD
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import load_env_file

load_env_file()

from werkzeug.security import generate_password_hash

from app.db.registry import STEP_REGISTRY, job_key

RUN_ID = 42
JOB_ID = 1
_RUN_DATE = datetime(2025, 5, 31, 2, 15, 0)


def _runtime() -> dict[str, tuple[str, str, int | None, str]]:
    from app.dashboard.mock_data import _RUNTIME

    return _RUNTIME


def _bootstrap_connect():
    import pyodbc

    server = os.environ.get("BOOTSTRAP_SERVER", "")
    database = os.environ.get("BOOTSTRAP_DATABASE", "")
    user = os.environ.get("BOOTSTRAP_USER", "")
    password = os.environ.get("BOOTSTRAP_PASSWORD", "")
    driver = os.environ.get("BOOTSTRAP_DRIVER", "ODBC Driver 18 for SQL Server")
    trust = os.environ.get("BOOTSTRAP_TRUST_CERT", "yes")

    if not all([server, database, user]):
        raise SystemExit(
            "Set BOOTSTRAP_SERVER, BOOTSTRAP_DATABASE, and BOOTSTRAP_USER in .env"
        )

    conn_str = ";".join(
        [
            f"DRIVER={{{driver}}}",
            f"SERVER={server}",
            f"DATABASE={database}",
            f"UID={user}",
            f"PWD={password}",
            f"TrustServerCertificate={trust}",
        ]
    )
    return pyodbc.connect(conn_str, timeout=60)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _seconds_after(seconds: int) -> datetime:
    return _RUN_DATE + timedelta(seconds=seconds)


def seed(db) -> None:
    cursor = db.cursor()

    # dbo.users
    users = [
        ("admin", "admin123", "Admin"),
        ("viewer", "viewer123", "ReadOnly"),
        ("jmorgan", "changeme", "Admin"),
    ]
    for username, password, role in users:
        ph = generate_password_hash(password)
        cursor.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE username = ?)
            INSERT INTO dbo.users (username, password_hash, role, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (username, username, ph, role),
        )

    # orchestration.app_connections — values from env only
    connections = [
        (
            "PRIMARY",
            _require_env("SEED_PRIMARY_SERVER"),
            _require_env("SEED_PRIMARY_DATABASE"),
            _require_env("SEED_PRIMARY_USER"),
            os.environ.get("SEED_PRIMARY_PASSWORD", ""),
        ),
        (
            "REMOTE_SQL",
            _require_env("SEED_REMOTE_SERVER"),
            _require_env("SEED_REMOTE_DATABASE"),
            _require_env("SEED_REMOTE_USER"),
            os.environ.get("SEED_REMOTE_PASSWORD", ""),
        ),
    ]
    for name, server, database, user, password in connections:
        cursor.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM orchestration.app_connections WHERE connection_name = ?)
            INSERT INTO orchestration.app_connections
                (connection_name, server_name, database_name, username, password_plain, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (name, name, server, database, user, password or None),
        )

    # orchestration.jobs
    cursor.execute("SET IDENTITY_INSERT orchestration.jobs ON")
    cursor.execute(
        """
        IF NOT EXISTS (SELECT 1 FROM orchestration.jobs WHERE job_id = ?)
        INSERT INTO orchestration.jobs (job_id, job_name, description, is_active)
        VALUES (?, N'RRA Month-End Orchestration', N'End-to-end month-end close orchestration.', 1)
        """,
        (JOB_ID, JOB_ID),
    )
    cursor.execute("SET IDENTITY_INSERT orchestration.jobs OFF")

    # orchestration.job_steps from registry
    cursor.execute("SET IDENTITY_INSERT orchestration.job_steps ON")
    order_by_phase: dict[str, int] = {}
    server_cache: dict[str, str] = {}
    for step_id, step in enumerate(STEP_REGISTRY, start=1):
        if step.connection_name not in server_cache:
            cursor.execute(
                "SELECT server_name FROM orchestration.app_connections WHERE connection_name = ?",
                (step.connection_name,),
            )
            row = cursor.fetchone()
            server_cache[step.connection_name] = row[0] if row else "unknown"
        order = order_by_phase.get(step.phase_code, 0) + 1
        order_by_phase[step.phase_code] = order
        cursor.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM orchestration.job_steps WHERE step_id = ?)
            INSERT INTO orchestration.job_steps
                (step_id, job_id, step_name, phase_code, server_name, step_order,
                 execute_proc_name, validate_proc_name, is_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                step_id,
                step_id,
                JOB_ID,
                step.step_name,
                step.phase_code,
                server_cache[step.connection_name],
                order,
                step.execute_proc,
                step.validate_proc,
            ),
        )
        if step.agent_job:
            cursor.execute(
                """
                IF NOT EXISTS (SELECT 1 FROM orchestration.monitored_agent_jobs WHERE job_name = ?)
                INSERT INTO orchestration.monitored_agent_jobs (job_name, connection_name)
                VALUES (?, ?)
                """,
                (step.agent_job, step.agent_job, step.connection_name),
            )

    cursor.execute("SET IDENTITY_INSERT orchestration.job_steps OFF")

    # orchestration.job_runs
    cursor.execute("SET IDENTITY_INSERT orchestration.job_runs ON")
    cursor.execute(
        """
        IF NOT EXISTS (SELECT 1 FROM orchestration.job_runs WHERE run_id = ?)
        INSERT INTO orchestration.job_runs
            (run_id, job_id, period_label, status, started_at, started_by)
        VALUES (?, ?, N'May 2025', N'In Progress', ?, N'admin')
        """,
        (RUN_ID, RUN_ID, JOB_ID, _RUN_DATE),
    )
    cursor.execute("SET IDENTITY_INSERT orchestration.job_runs OFF")

    # orchestration.step_runs
    cursor.execute("SET IDENTITY_INSERT orchestration.step_runs ON")
    runtime = _runtime()
    elapsed = 0
    for step_id, step in enumerate(STEP_REGISTRY, start=1):
        exec_status, val_status, duration, message = runtime[step.execute_proc]
        started_at = None
        completed_at = None
        if exec_status in ("Success", "Failed"):
            started_at = _seconds_after(elapsed)
            elapsed += (duration or 0) + 5
            completed_at = _seconds_after(elapsed)
        elif exec_status == "Running":
            started_at = _seconds_after(elapsed)

        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM orchestration.step_runs
                WHERE run_id = ? AND step_id = ?
            )
            INSERT INTO orchestration.step_runs
                (step_run_id, run_id, step_id, execution_status, validation_status,
                 last_message, duration_seconds, started_at, completed_at, run_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, N'admin')
            """,
            (
                RUN_ID,
                step_id,
                1000 + step_id,
                RUN_ID,
                step_id,
                exec_status,
                val_status,
                message,
                duration,
                started_at,
                completed_at,
            ),
        )

    cursor.execute("SET IDENTITY_INSERT orchestration.step_runs OFF")

    # orchestration.run_metrics
    runs = list(runtime.values())
    total = len(STEP_REGISTRY)
    success = sum(1 for e, _, _, _ in runs if e == "Success")
    failed = sum(1 for e, _, _, _ in runs if e == "Failed")
    running = sum(1 for e, _, _, _ in runs if e == "Running")
    pending = total - success - failed - running
    val_failed = sum(1 for _, v, _, _ in runs if v == "Failed")
    progress = round((success / total) * 100) if total else 0
    cursor.execute(
        """
        IF NOT EXISTS (SELECT 1 FROM orchestration.run_metrics WHERE run_id = ?)
        INSERT INTO orchestration.run_metrics
            (run_id, total_steps, success_count, failed_count, running_count,
             pending_count, validation_failed_count, progress_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            RUN_ID,
            RUN_ID,
            total,
            success,
            failed,
            running,
            pending,
            val_failed,
            progress,
        ),
    )

    db.commit()
    print("Seed complete.")


def main() -> None:
    print("Connecting via bootstrap credentials...")
    db = _bootstrap_connect()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
