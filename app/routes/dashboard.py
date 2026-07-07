"""Dashboard routes — Step 2: operations console layout.

Read-only layout wired to mock data. Execution/validation actions are not
implemented yet (Steps 6–7); the Run/Validate controls are rendered for Admin
users only but do not trigger any logic.
"""

from flask import Blueprint, render_template

from app.auth.decorators import login_required
from app.dashboard.service import DashboardService

dashboard_bp = Blueprint("dashboard", __name__)
dashboard_service = DashboardService()


@dashboard_bp.route("/dashboard")
@login_required
def index():
    data = dashboard_service.get_dashboard()
    return render_template(
        "dashboard/index.html",
        run=data["run"],
        metrics=data["metrics"],
        phases=data["phases"],
        execution_log=data["execution_log"],
        run_history=data["run_history"],
        active_connection=data["active_connection"],
    )
