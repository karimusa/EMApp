"""Authentication + user service — backed by ``dbo.users``."""

from __future__ import annotations

from typing import Any, Optional

from app.dashboard import data
from app.db.repositories.base import use_mock_data
from app.db.repositories.users import UserRepository


class AuthService:
    def __init__(self) -> None:
        self._repo = UserRepository()

    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        if use_mock_data():
            for user in data.get_users():
                if user["username"].lower() == username.lower():
                    return user
            return None
        return self._repo.get_by_username(username)

    def verify_password(self, user: dict[str, Any], password: str) -> bool:
        return self._repo.verify_password(user, password)

    def list_users(self) -> list[dict[str, Any]]:
        if use_mock_data():
            return [
                {k: v for k, v in user.items() if k != "password_hash"}
                for user in data.get_users()
            ]
        return self._repo.list_users()
