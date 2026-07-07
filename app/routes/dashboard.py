"""Orchestration dashboard routes."""

from flask import Blueprint, render_template, request

from app.auth.decorators import is_admin, login_required
from app.db.repositories.orchestration import OrchestrationRepository

dashboard_bp = Blueprint("dashboard", __name__)
orchestration_repo = OrchestrationRepository()


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    phase = request.args.get("phase", "PRE")
    current_run = orchestration_repo.get_current_run()
    steps = orchestration_repo.get_job_steps(phase=phase if phase != "ALL" else None)
    logs = orchestration_repo.get_execution_log(limit=50)
    metrics = orchestration_repo.get_run_metrics()
    phases = ("PRE", "MAIN", "BI", "DAY5", "POST")

    return render_template(
        "dashboard/index.html",
        current_run=current_run,
        steps=steps,
        logs=logs,
        metrics=metrics,
        active_phase=phase,
        phases=phases,
        is_admin=is_admin(),
    )
