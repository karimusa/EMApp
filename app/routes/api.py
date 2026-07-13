"""JSON API — data contracts for MonthEndOrchestrationDB integration.

Mock responses today use the same shapes the live SQL repositories will return.
"""

import logging

from flask import Blueprint, jsonify, request, session

from app.admin.errors import LiveDataRequiredError, UserAdminError
from app.auth.decorators import login_required
from app.auth.service import AuthService
from app.dashboard.errors import ExecutionError, LiveExecutionRequiredError
from app.dashboard.execution import ExecutionService
from app.dashboard.service import DashboardService
from app.db.repositories.base import use_mock_data

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
dashboard_service = DashboardService()
auth_service = AuthService()
execution_service = ExecutionService()
logger = logging.getLogger(__name__)


def _require_admin():
    if session.get("role") != "Admin":
        return jsonify({"error": "Permission denied.", "reason": "permission_denied"}), 403
    return None


def _user_admin_error_response(exc: Exception):
    if isinstance(exc, LiveDataRequiredError):
        return jsonify({"error": str(exc), "reason": "live_connection_unavailable"}), 503
    if isinstance(exc, UserAdminError):
        return jsonify({"error": str(exc), "reason": "validation_error"}), 400
    if isinstance(exc, ConnectionError):
        return jsonify({"error": str(exc), "reason": "database_connection_failed"}), 503
    return jsonify({"error": str(exc), "reason": "database_write_failed"}), 500


def _execution_error_response(exc: Exception):
    if isinstance(exc, LiveExecutionRequiredError):
        return jsonify({"error": str(exc), "reason": "live_connection_unavailable"}), 503
    if isinstance(exc, ExecutionError):
        return jsonify({"error": str(exc), "reason": "validation_error"}), 400
    if isinstance(exc, ConnectionError):
        return jsonify({"error": str(exc), "reason": "database_connection_failed"}), 503
    return jsonify({"error": str(exc), "reason": "execution_failed"}), 500


@api_bp.route("/execution/state")
@login_required
def execution_state():
    denied = _require_admin()
    if denied:
        return denied
    return jsonify(execution_service.get_execution_state())


@api_bp.route("/runs", methods=["POST"])
@login_required
def start_run():
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    logger.info(
        "API start_run user=%s payload=%s",
        session.get("username"),
        payload,
    )
    try:
        result = execution_service.start_run(
            actor=session.get("username") or "admin",
            run_name=payload.get("run_name"),
        )
        logger.info("API start_run success run_id=%s", result.get("run_id"))
        return jsonify({"run": result, "data_source": "live"}), 201
    except (LiveExecutionRequiredError, ExecutionError, ConnectionError) as exc:
        logger.warning("API start_run failed: %s", exc)
        return _execution_error_response(exc)
    except Exception as exc:
        logger.exception("API start_run error")
        return _execution_error_response(exc)


@api_bp.route("/runs/<int:run_id>/stop", methods=["POST"])
@login_required
def stop_run(run_id: int):
    denied = _require_admin()
    if denied:
        return denied
    logger.info("API stop_run user=%s run_id=%s", session.get("username"), run_id)
    try:
        result = execution_service.stop_run(
            run_id=run_id,
            actor=session.get("username") or "admin",
        )
        logger.info("API stop_run success run_id=%s", run_id)
        return jsonify({"run": result, "data_source": "live"})
    except (LiveExecutionRequiredError, ExecutionError, ConnectionError) as exc:
        logger.warning("API stop_run failed: %s", exc)
        return _execution_error_response(exc)
    except Exception as exc:
        logger.exception("API stop_run error")
        return _execution_error_response(exc)


@api_bp.route("/runs/sequence", methods=["POST"])
@login_required
def run_sequence():
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    try:
        result = execution_service.run_sequence(
            run_id=payload.get("run_id"),
            actor=session.get("username") or "admin",
        )
        return jsonify({"sequence": result, "data_source": "live"})
    except (LiveExecutionRequiredError, ExecutionError, ConnectionError) as exc:
        return _execution_error_response(exc)
    except Exception as exc:
        return _execution_error_response(exc)


@api_bp.route("/steps/<int:step_id>/run", methods=["POST"])
@login_required
def run_step(step_id: int):
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    logger.info(
        "API run_step user=%s step_id=%s payload=%s",
        session.get("username"),
        step_id,
        payload,
    )
    try:
        result = execution_service.run_step(
            step_id,
            run_id=payload.get("run_id"),
            actor=session.get("username") or "admin",
        )
        return jsonify({"step": result, "data_source": "live"})
    except (LiveExecutionRequiredError, ExecutionError, ConnectionError) as exc:
        return _execution_error_response(exc)
    except Exception as exc:
        return _execution_error_response(exc)


@api_bp.route("/steps/<int:step_id>/validate", methods=["POST"])
@login_required
def validate_step(step_id: int):
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    try:
        result = execution_service.validate_step(
            step_id,
            run_id=payload.get("run_id"),
            actor=session.get("username") or "admin",
        )
        return jsonify({"step": result, "data_source": "live"})
    except (LiveExecutionRequiredError, ExecutionError, ConnectionError) as exc:
        return _execution_error_response(exc)
    except Exception as exc:
        return _execution_error_response(exc)


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


@api_bp.route("/users", methods=["GET"])
@login_required
def users():
    denied = _require_admin()
    if denied:
        return denied
    return jsonify(
        {
            "users": auth_service.list_users(),
            "data_source": "mock" if use_mock_data() else "live",
        }
    )


@api_bp.route("/users", methods=["POST"])
@login_required
def create_user():
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    try:
        user = auth_service.create_user(
            username=payload.get("username", ""),
            display_name=payload.get("display_name", ""),
            email=payload.get("email", ""),
            role=payload.get("role", "ReadOnly"),
            password=payload.get("password", ""),
            actor_user_id=session.get("user_id"),
        )
        return jsonify({"user": user, "data_source": "live"}), 201
    except (LiveDataRequiredError, UserAdminError, ConnectionError) as exc:
        return _user_admin_error_response(exc)
    except Exception as exc:
        return _user_admin_error_response(exc)


@api_bp.route("/users/<int:user_id>", methods=["PATCH"])
@login_required
def update_user(user_id: int):
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    try:
        user = auth_service.update_user_profile(
            user_id,
            display_name=payload.get("display_name", ""),
            email=payload.get("email", ""),
            actor_user_id=session.get("user_id"),
        )
        return jsonify({"user": user, "data_source": "live"})
    except (LiveDataRequiredError, UserAdminError, ConnectionError) as exc:
        return _user_admin_error_response(exc)
    except Exception as exc:
        return _user_admin_error_response(exc)


@api_bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
def change_user_role(user_id: int):
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    try:
        user = auth_service.change_user_role(
            user_id,
            role=payload.get("role", ""),
            actor_user_id=session.get("user_id"),
        )
        return jsonify({"user": user, "data_source": "live"})
    except (LiveDataRequiredError, UserAdminError, ConnectionError) as exc:
        return _user_admin_error_response(exc)
    except Exception as exc:
        return _user_admin_error_response(exc)


@api_bp.route("/users/<int:user_id>/password", methods=["POST"])
@login_required
def reset_user_password(user_id: int):
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    try:
        auth_service.reset_user_password(
            user_id,
            password=payload.get("password", ""),
            actor_user_id=session.get("user_id"),
        )
        return jsonify({"ok": True, "data_source": "live"})
    except (LiveDataRequiredError, UserAdminError, ConnectionError) as exc:
        return _user_admin_error_response(exc)
    except Exception as exc:
        return _user_admin_error_response(exc)


@api_bp.route("/users/<int:user_id>/active", methods=["POST"])
@login_required
def set_user_active(user_id: int):
    denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    try:
        user = auth_service.set_user_active(
            user_id,
            is_active=bool(payload.get("is_active", True)),
            actor_user_id=session.get("user_id"),
        )
        return jsonify({"user": user, "data_source": "live"})
    except (LiveDataRequiredError, UserAdminError, ConnectionError) as exc:
        return _user_admin_error_response(exc)
    except Exception as exc:
        return _user_admin_error_response(exc)
