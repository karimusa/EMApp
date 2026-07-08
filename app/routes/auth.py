"""Authentication routes — Step 1: login page."""

import logging

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.auth.decorators import login_required
from app.auth.service import AuthService
from app.db.connection_manager import get_connection_manager, is_pyodbc_error
from app.db.repositories.base import use_mock_data

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)
auth_service = AuthService()


def _database_unavailable_message() -> str:
    return (
        "The application database is not reachable. "
        "Verify orchestration.app_connections credentials for PRIMARY "
        "(sql_username / sql_password_encrypted) or contact your administrator."
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    config_error = None
    if not use_mock_data():
        try:
            manager = get_connection_manager()
            manager.validate_primary()
            config_error = manager.get_primary_error()
        except RuntimeError:
            pass

    error = config_error
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if config_error:
            error = config_error
        elif not username or not password:
            error = "Username and password are required."
        else:
            try:
                user = auth_service.get_by_username(username)
            except ConnectionError as exc:
                logger.exception("Database connection error during login")
                error = str(exc) or _database_unavailable_message()
            except Exception as exc:
                if is_pyodbc_error(exc):
                    logger.exception("SQL error during login")
                    error = _database_unavailable_message()
                else:
                    raise
            else:
                if not user or not user.get("is_active"):
                    error = "Invalid username or password."
                elif not auth_service.verify_password(user, password):
                    error = "Invalid username or password."
                else:
                    session.clear()
                    session["user_id"] = user["user_id"]
                    session["username"] = user["username"]
                    session["role"] = user["role"]
                    session.permanent = True
                    next_url = (request.args.get("next") or "").strip()
                    if next_url.startswith("/") and not next_url.startswith("//"):
                        return redirect(next_url)
                    return redirect(url_for("dashboard.index"))

    return render_template(
        "auth/login.html",
        error=error,
        config_error=config_error,
    )


@auth_bp.route("/post-login")
@login_required
def post_login():
    """Legacy route — redirects to the operations console."""
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
