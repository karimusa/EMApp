"""Authentication + user service — backed by ``dbo.users``.

Reads the mock ``dbo.users`` rows today; swaps to live SQL later with no caller
changes. Passwords are stored/compared as hashes only.
"""

from __future__ import annotations

from typing import Any, Optional

from werkzeug.security import check_password_hash

from app.dashboard import mock_data

# Load the dbo.users rows once (hashing is expensive; the mock set is static).
_USERS: list[dict[str, Any]] = mock_data.get_users()


class AuthService:
    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        for user in _USERS:
            if user["username"].lower() == username.lower():
                return user
        return None

    def verify_password(self, user: dict[str, Any], password: str) -> bool:
        return check_password_hash(user["password_hash"], password)

    def list_users(self) -> list[dict[str, Any]]:
        """Return dbo.users rows without password hashes (for the admin screen)."""
        return [
            {k: v for k, v in user.items() if k != "password_hash"}
            for user in _USERS
        ]
