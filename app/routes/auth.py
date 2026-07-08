"""Authentication routes — Step 1: login page."""

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.auth.decorators import login_required
from app.auth.service import AuthService

auth_bp = Blueprint("auth", __name__)
auth_service = AuthService()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            error = "Username and password are required."
        else:
            user = auth_service.get_by_username(username)
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
                return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", error=error)


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
