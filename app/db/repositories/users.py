"""User repository — dbo.users."""

from __future__ import annotations

from typing import Any, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from app.db.connection_manager import get_connection_manager


class UserRepository:
    ROLES = ("Admin", "ReadOnly")

    def list_users(self) -> list[dict[str, Any]]:
        if self._testing():
            return self._mock_users()
        sql = """
            SELECT user_id, username, role, is_active, created_at, updated_at
            FROM dbo.users
            ORDER BY username
        """
        return self._query(sql)

    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        if self._testing():
            for user in self._mock_users(with_secrets=True):
                if user["username"].lower() == username.lower():
                    return user
            return None
        sql = """
            SELECT user_id, username, password_hash, role, is_active, created_at, updated_at
            FROM dbo.users
            WHERE username = ?
        """
        rows = self._query(sql, (username,))
        return rows[0] if rows else None

    def get_by_id(self, user_id: int) -> Optional[dict[str, Any]]:
        if self._testing():
            for user in self._mock_users():
                if user["user_id"] == user_id:
                    return user
            return None
        sql = """
            SELECT user_id, username, role, is_active, created_at, updated_at
            FROM dbo.users
            WHERE user_id = ?
        """
        rows = self._query(sql, (user_id,))
        return rows[0] if rows else None

    def create_user(self, username: str, password: str, role: str) -> int:
        password_hash = generate_password_hash(password)
        if self._testing():
            return 99
        sql = """
            INSERT INTO dbo.users (username, password_hash, role, is_active)
            OUTPUT INSERTED.user_id
            VALUES (?, ?, ?, 1)
        """
        with get_connection_manager().connect("PRIMARY") as db:
            cursor = db.cursor()
            cursor.execute(sql, (username, password_hash, role))
            row = cursor.fetchone()
            db.commit()
            return int(row[0])

    def update_user(self, user_id: int, role: str, is_active: bool) -> None:
        if self._testing():
            return
        sql = """
            UPDATE dbo.users
            SET role = ?, is_active = ?, updated_at = SYSUTCDATETIME()
            WHERE user_id = ?
        """
        self._execute(sql, (role, int(is_active), user_id))

    def change_password(self, user_id: int, new_password: str) -> None:
        password_hash = generate_password_hash(new_password)
        if self._testing():
            return
        sql = """
            UPDATE dbo.users
            SET password_hash = ?, updated_at = SYSUTCDATETIME()
            WHERE user_id = ?
        """
        self._execute(sql, (password_hash, user_id))

    def verify_password(self, user: dict[str, Any], password: str) -> bool:
        return check_password_hash(user.get("password_hash", ""), password)

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with get_connection_manager().connect("PRIMARY") as db:
            cursor = db.cursor()
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _execute(self, sql: str, params: tuple = ()) -> None:
        with get_connection_manager().connect("PRIMARY") as db:
            cursor = db.cursor()
            cursor.execute(sql, params)
            db.commit()

    def _testing(self) -> bool:
        try:
            return get_connection_manager()._config.get("TESTING", False)
        except RuntimeError:
            return False

    def _mock_users(self, with_secrets: bool = False) -> list[dict[str, Any]]:
        admin = {
            "user_id": 1,
            "username": "admin",
            "role": "Admin",
            "is_active": True,
            "created_at": None,
            "updated_at": None,
        }
        readonly = {
            "user_id": 2,
            "username": "viewer",
            "role": "ReadOnly",
            "is_active": True,
            "created_at": None,
            "updated_at": None,
        }
        if with_secrets:
            admin["password_hash"] = generate_password_hash("admin123")
            readonly["password_hash"] = generate_password_hash("viewer123")
        return [admin, readonly]
