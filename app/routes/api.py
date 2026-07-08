"""JSON API — data contracts for MonthEndOrchestrationDB integration.

Mock responses today use the same shapes the live SQL repositories will return.
"""

from flask import Blueprint, jsonify, session

from app.auth.decorators import login_required
from app.auth.service import AuthService
from app.dashboard.service import DashboardService

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
dashboard_service = DashboardService()
auth_service = AuthService()


def _require_admin():
    if session.get("role") != "Admin":
        return jsonify({"error": "Administrator access required."}), 403
    return None


@api_bp.route("/health")
def health():
    return jsonify({"status": "healthy", "app": "RRA Month-End Orchestration"}), 200


@api_bp.route("/me")
@login_required
def me():
    return jsonify(
        {
            "user_id": session.get("user_id"),
            "username": session.get("username"),
            "role": session.get("role"),
            "is_admin": session.get("role") == "Admin",
        }
    )


@api_bp.route("/dashboard")
@login_required
def dashboard():
    return jsonify(dashboard_service.get_dashboard())


@api_bp.route("/run-history")
@login_required
def run_history():
    return jsonify(dashboard_service.get_run_history())


@api_bp.route("/logs")
@login_required
def logs():
    return jsonify(dashboard_service.get_logs())


@api_bp.route("/agent-jobs")
@login_required
def agent_jobs():
    return jsonify(dashboard_service.get_agent_jobs())


@api_bp.route("/monitoring")
@login_required
def monitoring():
    return jsonify(dashboard_service.get_monitoring())


@api_bp.route("/validation")
@login_required
def validation():
    return jsonify(dashboard_service.get_validation())


@api_bp.route("/settings")
@login_required
def settings():
    return jsonify(dashboard_service.get_settings())


@api_bp.route("/users")
@login_required
def users():
    denied = _require_admin()
    if denied:
        return denied
    return jsonify({"users": auth_service.list_users()})
