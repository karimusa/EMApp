"""Administration routes — user management (Admin only)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth.decorators import admin_required
from app.db.repositories.users import UserRepository

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
user_repo = UserRepository()


@admin_bp.route("/users")
@admin_required
def users():
    return render_template("admin/users.html", users=user_repo.list_users())


@admin_bp.route("/users/add", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("role") or "ReadOnly"

        if not username or not password:
            flash("Username and password are required.", "danger")
        elif role not in UserRepository.ROLES:
            flash("Invalid role selected.", "danger")
        elif user_repo.get_by_username(username):
            flash("Username already exists.", "danger")
        else:
            user_repo.create_user(username, password, role)
            flash(f"User '{username}' created.", "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", user=None, roles=UserRepository.ROLES)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = user_repo.get_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if request.method == "POST":
        role = request.form.get("role") or user["role"]
        is_active = request.form.get("is_active") == "on"
        new_password = request.form.get("new_password") or ""

        if role not in UserRepository.ROLES:
            flash("Invalid role selected.", "danger")
        else:
            user_repo.update_user(user_id, role, is_active)
            if new_password:
                user_repo.change_password(user_id, new_password)
            flash(f"User '{user['username']}' updated.", "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", user=user, roles=UserRepository.ROLES)
