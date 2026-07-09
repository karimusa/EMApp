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

from app.db.credentials import is_one_way_hash, stored_credential_from_row
from config.bootstrap import (
    format_incomplete_bootstrap_message,
    load_bootstrap_config,
    print_bootstrap_validation,
    require_bootstrap_config,
    run_bootstrap_self_test_and_print,
)
from config.settings import build_runtime_config, load_env_file


def _primary_failure_hint(rows: list[dict]) -> str | None:
    primary = next(
        (r for r in rows if str(r.get("environment_name", "")).upper() == "PRIMARY"),
        None,
    )
    if not primary:
        return None
    stored = stored_credential_from_row(primary)
    if stored and is_one_way_hash(stored):
        return (
            "Hint: PRIMARY stores a one-way hash in sql_password_encrypted/"
            "sql_password_hash. When PRIMARY matches bootstrap server/database/user, "
            "BOOTSTRAP_PASSWORD is used automatically after you deploy the latest code. "
            "Otherwise replace the hash with the real SQL login password or Fernet "
            "ciphertext from scripts/encrypt_password.py."
        )
    if not stored:
        return (
            "Hint: PRIMARY has no sql_password_encrypted value. "
            "Set it in orchestration.app_connections or match bootstrap "
            "server/database/user so BOOTSTRAP_PASSWORD applies."
        )
    return None


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

    load_env_file()

    if args.connections_only:
        require_bootstrap_config()
        runtime = build_runtime_config()
        rows = run_bootstrap_self_test_and_print(runtime)

        from app import create_app
        from app.db.connection_manager import init_connection_manager
        from config.settings import DevelopmentConfig

        app = create_app(DevelopmentConfig)
        with app.app_context():
            cm = init_connection_manager(app)
            primary_error = cm.ensure_primary_validated(reload_registry=True)
            if primary_error:
                print(f"FAILED: PRIMARY connection: {primary_error}", file=sys.stderr)
                hint = _primary_failure_hint(rows)
                if hint:
                    print(hint, file=sys.stderr)
                return 1
            print("PRIMARY connection: SUCCESS")
        return 0

    bootstrap = print_bootstrap_validation()
    if not bootstrap.is_complete:
        print(format_incomplete_bootstrap_message(bootstrap), file=sys.stderr)
        print("Data source: mock", file=sys.stderr)
        print("Running mock read checks anyway...", file=sys.stderr)

        from app import create_app
        from app.dashboard import data
        from config.settings import DevelopmentConfig

        app = create_app(DevelopmentConfig)
        with app.app_context():
            print(f"\nData source: {data.data_source_label()}")
            print("\nRead-layer checks (mock):")
            _check("dbo.users", lambda: data.get_users())
            _check("orchestration.app_connections", lambda: data.get_app_connections())
        return 0

    runtime = build_runtime_config()
    run_bootstrap_self_test_and_print(runtime)

    from app import create_app
    from app.dashboard import data
    from app.db.connection_manager import init_connection_manager
    from config.settings import DevelopmentConfig

    app = create_app(DevelopmentConfig)
    with app.app_context():
        source = data.data_source_label()
        print(f"\nData source: {source}")
        if source == "mock":
            print(
                "ERROR: bootstrap is configured but app is still in mock mode.",
                file=sys.stderr,
            )
            return 1

        cm = init_connection_manager(app)
        primary_error = cm.ensure_primary_validated(reload_registry=True)
        conns = cm.all_connections()
        print(f"Loaded {len(conns)} runtime connection(s): {', '.join(conns.keys())}")
        for name, conn in conns.items():
            print(f"  {name}: {conn.environment_name} -> {conn.server_name} / {conn.database_name}")

        if primary_error:
            print(f"FAILED: PRIMARY connection: {primary_error}", file=sys.stderr)
            return 1
        print("  OK  PRIMARY connection")

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
    except SystemExit:
        raise
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
