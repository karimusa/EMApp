#!/usr/bin/env python3
"""Utility to encrypt a connection password for orchestration.app_connections."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.db.crypto import encrypt_password


def main():
    parser = argparse.ArgumentParser(description="Encrypt a SQL connection password")
    parser.add_argument("password", help="Plain-text password to encrypt")
    parser.add_argument(
        "--key",
        default=os.environ.get("CONNECTION_SECRET_KEY"),
        help="Fernet key (default: CONNECTION_SECRET_KEY env var)",
    )
    args = parser.parse_args()

    if not args.key:
        print("ERROR: Set CONNECTION_SECRET_KEY or pass --key", file=sys.stderr)
        sys.exit(1)

    print(encrypt_password(args.password, args.key))


if __name__ == "__main__":
    main()
