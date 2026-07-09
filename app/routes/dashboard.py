"""Dashboard routes — operations console pages.

All pages render against mock data shaped like the MonthEndOrchestrationDB
schema. The same view models are exposed as JSON under ``/api/v1/*`` for the
live SQL integration step.
"""

from flask import Blueprint, render_template

from app.auth.decorators import login_required
from app.dashboard.execution import ExecutionService
from app.dashboard.service import DashboardService
from app.db.repositories.base import use_mock_data

dashboard_bp = Blueprint("dashboard", __name__)
dashboard_service = DashboardService()
execution_service = ExecutionService()


@dashboard_bp.route("/dashboard")
@login_required
def index():
    data = dashboard_service.get_dashboard()
    execution_state = execution_service.get_execution_state()
    return render_template(
        "dashboard/index.html",
        run=data["run"],
        metrics=data["metrics"],
        phases=data["phases"],
        execution_log=data["execution_log"],
        run_history=data["run_history"],
        active_connection=data["active_connection"],
        live_db_available=execution_state["live_db_available"],
        active_run_id=execution_state["active_run_id"],
        can_stop_run=execution_state["can_stop"],
        can_run_sequence=execution_state["can_sequence"],
    )


@dashboard_bp.route("/run-history")
@login_required
def run_history():
    data = dashboard_service.get_run_history()
    return render_template(
        "dashboard/run_history.html",
        runs=data["runs"],
        totals=data["totals"],
        active_connection=data["active_connection"],
    )


@dashboard_bp.route("/agent-jobs")
@login_required
def agent_jobs():
    data = dashboard_service.get_agent_jobs()
    return render_template(
        "dashboard/agent_jobs.html",
        groups=data["groups"],
        totals=data["totals"],
        active_connection=data["active_connection"],
    )


@dashboard_bp.route("/logs")
@login_required
def logs():
    data = dashboard_service.get_logs()
    return render_template(
        "dashboard/logs.html",
        rows=data["rows"],
        phases=data["phases"],
        totals=data["totals"],
        active_connection=data["active_connection"],
    )


@dashboard_bp.route("/monitoring")
@login_required
def monitoring():
    data = dashboard_service.get_monitoring()
    return render_template(
        "dashboard/monitoring.html",
        run=data["run"],
        metrics=data["metrics"],
        connections=data["connections"],
        agent_jobs=data["agent_jobs"],
        active_connection=data["active_connection"],
    )


@dashboard_bp.route("/validation")
@login_required
def validation():
    data = dashboard_service.get_validation()
    return render_template(
        "dashboard/validation.html",
        rows=data["rows"],
        totals=data["totals"],
        active_connection=data["active_connection"],
    )


@dashboard_bp.route("/reports")
@login_required
def reports():
    return render_template("dashboard/reports.html")


@dashboard_bp.route("/settings")
@login_required
def settings():
    data = dashboard_service.get_settings()
    return render_template(
        "dashboard/settings.html",
        connections=data["connections"],
        app_version=data["app_version"],
        data_source=data["data_source"],
        active_connection=data["active_connection"],
    )
