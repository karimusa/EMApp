#!/usr/bin/env python3
"""Verify live SQL read layer — all screens' data contracts.

Usage:
  python scripts/verify_live_reads.py
  python scripts/verify_live_reads.py --connections-only

Requires bootstrap credentials in .env and seeded MonthEndOrchestrationDB tables.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import load_env_file

load_env_file()

from app import create_app
from app.dashboard import data
from app.db.connection_manager import init_connection_manager
from config.settings import DevelopmentConfig


def _check(label: str, fn) -> None:
    result = fn()
    if result is None:
        raise RuntimeError(f"{label} returned None")
    if isinstance(result, (list, dict)) and len(result) == 0:
        raise RuntimeError(f"{label} returned empty")
    print(f"  OK  {label}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify EMApp live SQL reads")
    parser.add_argument(
        "--connections-only",
        action="store_true",
        help="Only test bootstrap + orchestration.app_connections",
    )
    args = parser.parse_args()

    app = create_app(DevelopmentConfig)
    with app.app_context():
        source = data.data_source_label()
        print(f"Data source: {source}")
        if source == "mock":
            print("WARNING: DATA_SOURCE is mock — set BOOTSTRAP_SERVER in .env for live SQL.")
            if not args.connections_only:
                print("Running mock read checks anyway...")
        else:
            cm = init_connection_manager(app)
            cm.reload()
            conns = cm.all_connections()
            print(f"Loaded {len(conns)} connection(s): {', '.join(conns.keys())}")
            for name, conn in conns.items():
                print(f"  {name}: {conn.server_name} / {conn.database_name}")

        if args.connections_only:
            return 0

        print("\nRead-layer checks:")
        _check("dbo.users", lambda: data.get_users())
        _check("orchestration.app_connections", lambda: data.get_app_connections())
        _check("orchestration.jobs", lambda: data.get_jobs())
        _check("orchestration.job_steps", lambda: data.get_job_steps())
        _check("orchestration.job_runs", lambda: data.get_job_runs())
        _check("orchestration.step_runs", lambda: data.get_step_runs())
        _check("orchestration.db_execution_log", lambda: data.get_execution_log())
        _check("orchestration.run_metrics", lambda: data.get_run_metrics())
        _check("validation results", lambda: data.get_validation_results())
        _check("SQL Agent jobs", lambda: data.get_monitored_agent_jobs())
        _check("current run", lambda: data.get_current_run())

        print("\nAll read-layer checks passed.")
        print("Screens served: /login /dashboard /run-history /agent-jobs /logs")
        print("                /admin/users /monitoring /validation /settings")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
