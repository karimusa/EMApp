"""RRA Month-End Orchestration — incremental build."""

import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, redirect, session, url_for

from config.settings import Config


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)
    _configure_logging(app)

    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    from app.db.connection_manager import init_connection_manager

    init_connection_manager(app)

    @app.route("/")
    def root():
        if session.get("user_id"):
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_nav_globals():
        connection = None
        if session.get("user_id"):
            from app.dashboard.connections import ConnectionService

            connection = ConnectionService().get_active()
        return {
            "nav_user": {
                "username": session.get("username"),
                "role": session.get("role"),
            },
            "nav_is_admin": session.get("role") == "Admin",
            "nav_connection": connection,
        }

    return app


def _configure_logging(app):
    log_dir = app.config["LOGS_DIR"]
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "emapp.log", maxBytes=5_000_000, backupCount=5
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    app.logger.addHandler(handler)
