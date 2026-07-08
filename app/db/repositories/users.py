"""User repository — dbo.users."""

from __future__ import annotations

from typing import Any, Optional

from werkzeug.security import check_password_hash

from app.db.formatters import format_timestamp
from app.db.repositories.base import query_primary


class UserRepository:
    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        rows = query_primary(
            """
            SELECT user_id, username, password_hash, role, is_active, created_at, updated_at
            FROM dbo.users
            WHERE LOWER(username) = LOWER(?)
            """,
            (username,),
        )
        return self._normalize(rows[0]) if rows else None

    def list_users(self) -> list[dict[str, Any]]:
        rows = query_primary(
            """
            SELECT user_id, username, role, is_active, created_at, updated_at
            FROM dbo.users
            ORDER BY username
            """
        )
        return [self._normalize(row, include_hash=False) for row in rows]

    def verify_password(self, user: dict[str, Any], password: str) -> bool:
        return check_password_hash(user.get("password_hash", ""), password)

    def _normalize(self, row: dict[str, Any], include_hash: bool = True) -> dict[str, Any]:
        out = {
            "user_id": row["user_id"],
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
            "created_at": format_timestamp(row.get("created_at")),
            "updated_at": format_timestamp(row.get("updated_at")),
        }
        if include_hash and "password_hash" in row:
            out["password_hash"] = row["password_hash"]
        return out
