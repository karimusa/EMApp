#!/usr/bin/env python3
"""Encrypt a connection password for orchestration.app_connections."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.db.crypto import encrypt_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt a SQL connection password")
    parser.add_argument("password", help="Plain-text password to encrypt")
    parser.add_argument(
        "--key",
        default=os.environ.get("CONNECTION_SECRET_KEY"),
        help="Fernet key (default: CONNECTION_SECRET_KEY env var)",
    )
    args = parser.parse_args()

    if not args.key:
        print("ERROR: Set CONNECTION_SECRET_KEY in .env or pass --key", file=sys.stderr)
        sys.exit(1)

    print(encrypt_password(args.password, args.key))


if __name__ == "__main__":
    main()
