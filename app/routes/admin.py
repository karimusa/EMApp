"""Admin routes — user management (Admin only)."""

from flask import Blueprint, render_template, session

from app.auth.decorators import admin_required
from app.auth.service import AuthService
from app.db.repositories.base import use_mock_data

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
auth_service = AuthService()


@admin_bp.route("/users")
@admin_required
def users():
    live_db_available = not use_mock_data()
    return render_template(
        "admin/users.html",
        users=auth_service.list_users(),
        live_db_available=live_db_available,
        data_source="live" if live_db_available else "mock",
        current_user_id=session.get("user_id"),
    )
