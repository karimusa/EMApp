"""Authentication service — mock users until database connection step."""

from __future__ import annotations

from typing import Any, Optional

from werkzeug.security import check_password_hash, generate_password_hash

# Step 1: in-memory users for design/testing. Replaced by dbo.users in a later step.
_MOCK_USERS: list[dict[str, Any]] = [
    {
        "user_id": 1,
        "username": "admin",
        "password_hash": generate_password_hash("admin123"),
        "role": "Admin",
        "is_active": True,
    },
    {
        "user_id": 2,
        "username": "viewer",
        "password_hash": generate_password_hash("viewer123"),
        "role": "ReadOnly",
        "is_active": True,
    },
]


class AuthService:
    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        for user in _MOCK_USERS:
            if user["username"].lower() == username.lower():
                return user
        return None

    def verify_password(self, user: dict[str, Any], password: str) -> bool:
        return check_password_hash(user["password_hash"], password)
