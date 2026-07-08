"""Admin routes — user management (Admin only).

Step 2 renders the ``dbo.users`` roster and role-gated management controls.
Mutations (add/edit/deactivate) are wired in a later step; the controls here are
visible to Admins only and currently surface a notice.
"""

from flask import Blueprint, render_template

from app.auth.decorators import admin_required
from app.auth.service import AuthService

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
auth_service = AuthService()


@admin_bp.route("/users")
@admin_required
def users():
    return render_template("admin/users.html", users=auth_service.list_users())
