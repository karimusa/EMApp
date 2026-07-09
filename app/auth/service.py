"""Authentication + user service — backed by ``dbo.users``."""

from __future__ import annotations

from typing import Any, Optional

from app.admin.errors import LiveDataRequiredError, UserAdminError
from app.auth.passwords import is_legacy_sha256_password_hash
from app.dashboard import data
from app.db.repositories.base import use_mock_data
from app.db.repositories.users import UserRepository

_ALLOWED_ROLES = frozenset({"Admin", "ReadOnly"})
_MIN_PASSWORD_LEN = 6


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

    def upgrade_legacy_password_if_needed(
        self,
        user: dict[str, Any],
        password: str,
    ) -> None:
        if use_mock_data():
            return
        stored = user.get("password_hash")
        if not is_legacy_sha256_password_hash(stored):
            return
        self._repo.upgrade_password_hash(user["user_id"], password)

    def list_users(self) -> list[dict[str, Any]]:
        if use_mock_data():
            return [
                {k: v for k, v in user.items() if k != "password_hash"}
                for user in data.get_users()
            ]
        return self._repo.list_users()

    def get_user(self, user_id: int) -> Optional[dict[str, Any]]:
        if use_mock_data():
            for user in data.get_users():
                if int(user["user_id"]) == int(user_id):
                    return {k: v for k, v in user.items() if k != "password_hash"}
            return None
        return self._repo.get_by_id(user_id)

    def _require_live_data(self) -> None:
        if use_mock_data():
            raise LiveDataRequiredError(
                "Live SQL connection unavailable. User management requires "
                "MonthEndOrchestrationDB."
            )

    @staticmethod
    def _validate_role(role: str) -> str:
        normalized = (role or "").strip()
        if normalized not in _ALLOWED_ROLES:
            raise UserAdminError("Role must be Admin or ReadOnly.")
        return normalized

    @staticmethod
    def _validate_password(password: str) -> str:
        value = password or ""
        if len(value) < _MIN_PASSWORD_LEN:
            raise UserAdminError(
                f"Password must be at least {_MIN_PASSWORD_LEN} characters."
            )
        return value

    def create_user(
        self,
        *,
        username: str,
        password: str,
        role: str,
        display_name: str | None = None,
        email: str | None = None,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._require_live_data()
        name = (username or "").strip()
        if not name:
            raise UserAdminError("Username is required.")
        if self._repo.get_by_username(name):
            raise UserAdminError("Username already exists.")
        validated_role = self._validate_role(role)
        validated_password = self._validate_password(password)
        return self._repo.create_user(
            username=name,
            password=validated_password,
            role=validated_role,
            display_name=display_name,
            email=email,
        )

    def update_user_profile(
        self,
        user_id: int,
        *,
        display_name: str,
        email: str,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._require_live_data()
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserAdminError("User not found.")
        display = (display_name or user["username"]).strip()
        if not display:
            raise UserAdminError("Display name is required.")
        self._repo.update_profile(
            user_id,
            display_name=display,
            email=(email or "").strip(),
        )
        updated = self._repo.get_by_id(user_id)
        if not updated:
            raise UserAdminError("User not found after update.")
        return {k: v for k, v in updated.items() if k != "password_hash"}

    def change_user_role(
        self,
        user_id: int,
        *,
        role: str,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._require_live_data()
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserAdminError("User not found.")
        validated_role = self._validate_role(role)
        if actor_user_id is not None and int(actor_user_id) == int(user_id):
            if validated_role != user["role"]:
                raise UserAdminError("You cannot change your own role.")
        self._repo.update_role(user_id, validated_role)
        updated = self._repo.get_by_id(user_id)
        if not updated:
            raise UserAdminError("User not found after role change.")
        return {k: v for k, v in updated.items() if k != "password_hash"}

    def reset_user_password(
        self,
        user_id: int,
        *,
        password: str,
        actor_user_id: int | None = None,
    ) -> None:
        self._require_live_data()
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserAdminError("User not found.")
        validated_password = self._validate_password(password)
        self._repo.upgrade_password_hash(user_id, validated_password)

    def set_user_active(
        self,
        user_id: int,
        *,
        is_active: bool,
        actor_user_id: int | None = None,
    ) -> dict[str, Any]:
        self._require_live_data()
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserAdminError("User not found.")
        if actor_user_id is not None and int(actor_user_id) == int(user_id):
            if not is_active:
                raise UserAdminError("You cannot disable your own account.")
        self._repo.set_active(user_id, is_active)
        updated = self._repo.get_by_id(user_id)
        if not updated:
            raise UserAdminError("User not found after status change.")
        return {k: v for k, v in updated.items() if k != "password_hash"}

    def touch_last_login(self, user_id: int) -> None:
        if use_mock_data():
            return
        self._repo.touch_last_login(user_id)
