"""Dashboard routes — operations console."""

from flask import Blueprint, render_template

from app.auth.decorators import admin_required, login_required
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


@dashboard_bp.route("/runs")
@login_required
def runs():
    data = dashboard_service.get_runs_page()
    return render_template("dashboard/runs.html", **data)


@dashboard_bp.route("/steps")
@login_required
def steps():
    data = dashboard_service.get_steps_page()
    return render_template("dashboard/steps.html", **data)


@dashboard_bp.route("/logs")
@login_required
def logs():
    data = dashboard_service.get_logs_page()
    return render_template("dashboard/logs.html", **data)


@dashboard_bp.route("/monitoring")
@login_required
def monitoring():
    data = dashboard_service.get_monitoring_page()
    return render_template("dashboard/monitoring.html", **data)


@dashboard_bp.route("/validations")
@login_required
def validations():
    data = dashboard_service.get_validations_page()
    return render_template("dashboard/validations.html", **data)


@dashboard_bp.route("/alerts")
@login_required
def alerts():
    data = dashboard_service.get_alerts_page()
    return render_template("dashboard/alerts.html", **data)


@dashboard_bp.route("/reports")
@login_required
def reports():
    data = dashboard_service.get_reports_page()
    return render_template("dashboard/reports.html", **data)


@dashboard_bp.route("/servers")
@login_required
def servers():
    data = dashboard_service.get_servers_page()
    return render_template("dashboard/servers.html", **data)


@dashboard_bp.route("/settings")
@login_required
def settings():
    data = dashboard_service.get_settings_page()
    return render_template("dashboard/settings.html", **data)


@dashboard_bp.route("/audit-logs")
@login_required
def audit_logs():
    data = dashboard_service.get_audit_page()
    return render_template("dashboard/audit_logs.html", **data)
