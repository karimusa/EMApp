#!/usr/bin/env python3
"""Verify the PRIMARY credential fix is present in the deployed tree.

Run from the project root (e.g. G:\\EM):

  python scripts\\verify_deployed_code.py

Exits 0 when required runtime-credential symbols are found in source files.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_MARKERS: dict[str, list[str]] = {
    "app/routes/auth.py": [
        "ensure_primary_validated",
        "_login_config_error",
        "sql_connection_error_message",
    ],
    "app/db/connection_manager.py": [
        "ensure_primary_validated",
        "_runtime_sql_credentials",
        "is_unusable_stored_credential",
    ],
    "app/db/credentials.py": [
        "is_unusable_stored_credential",
        "BOOTSTRAP_PASSWORD",
    ],
    "app/db/repositories/base.py": [
        "ensure_primary_validated",
        "sql_connection_error_message",
    ],
}

FORBIDDEN_MARKERS: dict[str, list[str]] = {
    "app/db/connection_manager.py": [
        "build_connection_string(conn_info), timeout=30)",
    ],
}


def main() -> int:
    missing: list[str] = []
    stale: list[str] = []

    for rel_path, markers in REQUIRED_MARKERS.items():
        path = ROOT / rel_path
        if not path.is_file():
            missing.append(f"{rel_path} (file missing)")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker not in text:
                missing.append(f"{rel_path}: missing `{marker}`")

    for rel_path, markers in FORBIDDEN_MARKERS.items():
        path = ROOT / rel_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker in text:
                stale.append(f"{rel_path}: still contains old code `{marker}`")

    if missing or stale:
        print("DEPLOYED CODE CHECK: FAILED", file=sys.stderr)
        for item in missing:
            print(f"  missing: {item}", file=sys.stderr)
        for item in stale:
            print(f"  stale: {item}", file=sys.stderr)
        print(
            "\nPull the latest main branch and restart the app:\n"
            "  cd G:\\EM\n"
            "  git pull origin main\n"
            "  .\\setup.ps1 -TestConnection",
            file=sys.stderr,
        )
        return 1

    print("DEPLOYED CODE CHECK: OK")
    print("PRIMARY runtime credential fix is present in this tree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
