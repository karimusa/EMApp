"""Authentication routes."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.auth.decorators import login_required
from app.db.repositories.users import UserRepository

auth_bp = Blueprint("auth", __name__)
user_repo = UserRepository()


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
            user = user_repo.get_by_username(username)
            if not user or not user.get("is_active"):
                error = "Invalid username or password."
            elif not user_repo.verify_password(user, password):
                error = "Invalid username or password."
            else:
                session.clear()
                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["role"] = user["role"]
                session.permanent = True
                flash(f"Welcome, {user['username']}.", "success")
                next_url = request.args.get("next") or url_for("dashboard.index")
                return redirect(next_url)

    return render_template("auth/login.html", error=error)


@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
