"""User repository — dbo.users."""

from __future__ import annotations

from typing import Any, Optional

from werkzeug.security import check_password_hash

from app.db.live_schema import USERS_COLUMNS, normalize_user_row
from app.db.repositories.base import exec_primary, query_primary


class UserRepository:
    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        columns = ", ".join(USERS_COLUMNS)
        rows = query_primary(
            f"""
            SELECT {columns}
            FROM dbo.users
            WHERE LOWER(username) = LOWER(?)
            """,
            (username,),
        )
        return normalize_user_row(rows[0]) if rows else None

    def list_users(self) -> list[dict[str, Any]]:
        columns = ", ".join(
            col for col in USERS_COLUMNS if col not in {"password_hash"}
        )
        rows = query_primary(
            f"""
            SELECT {columns}
            FROM dbo.users
            ORDER BY username
            """
        )
        return [normalize_user_row(row, include_hash=False) for row in rows]

    def verify_password(self, user: dict[str, Any], password: str) -> bool:
        return check_password_hash(user.get("password_hash", ""), password)

    def touch_last_login(self, user_id: int) -> None:
        exec_primary(
            """
            UPDATE dbo.users
            SET last_login = SYSUTCDATETIME()
            WHERE user_id = ?
            """,
            (user_id,),
        )
