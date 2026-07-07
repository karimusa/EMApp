"""API routes for AJAX / HTMX orchestration actions."""

from flask import Blueprint, jsonify, render_template, request, session

from app.auth.decorators import admin_required, login_required
from app.db.repositories.orchestration import OrchestrationRepository

api_bp = Blueprint("api", __name__, url_prefix="/api")
orchestration_repo = OrchestrationRepository()


@api_bp.route("/steps")
@login_required
def list_steps():
    phase = request.args.get("phase")
    steps = orchestration_repo.get_job_steps(phase=phase)
    return jsonify(steps)


@api_bp.route("/steps/<int:step_id>/execute", methods=["POST"])
@admin_required
def execute_step(step_id):
    username = session.get("username", "system")
    try:
        result = orchestration_repo.execute_step(step_id, username)
        return jsonify({"success": True, "result": result})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/steps/<int:step_id>/validate", methods=["POST"])
@admin_required
def validate_step(step_id):
    username = session.get("username", "system")
    try:
        result = orchestration_repo.validate_step(step_id, username)
        return jsonify({"success": True, "result": result})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@api_bp.route("/logs")
@login_required
def get_logs():
    limit = int(request.args.get("limit", 50))
    logs = orchestration_repo.get_execution_log(limit=limit)
    if request.headers.get("HX-Request"):
        return render_template("partials/log_panel.html", logs=logs)
    return jsonify(logs)


@api_bp.route("/metrics")
@login_required
def get_metrics():
    metrics = orchestration_repo.get_run_metrics()
    if request.headers.get("HX-Request"):
        return render_template("partials/metrics_panel.html", metrics=metrics)
    return jsonify(metrics)


@api_bp.route("/run-status")
@login_required
def run_status():
    current_run = orchestration_repo.get_current_run()
    if request.headers.get("HX-Request"):
        return render_template("partials/run_header.html", current_run=current_run)
    return jsonify(current_run or {})


@api_bp.route("/steps/partial")
@login_required
def steps_partial():
    phase = request.args.get("phase", "PRE")
    steps = orchestration_repo.get_job_steps(phase=phase)
    is_admin = session.get("role") == "Admin"
    return render_template(
        "partials/step_grid.html",
        steps=steps,
        active_phase=phase,
        is_admin=is_admin,
    )
