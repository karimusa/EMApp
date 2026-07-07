"""RRA Month-End Orchestration web application."""

import logging
from logging.handlers import RotatingFileHandler

from flask import Flask

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

    from app.db.connection_manager import init_connection_manager

    init_connection_manager(app)

    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.jobs import jobs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_globals():
        from flask import session

        return {
            "current_username": session.get("username"),
            "current_role": session.get("role"),
            "is_admin": session.get("role") == "Admin",
        }

    return app


def _configure_logging(app):
    log_dir = app.config["LOGS_DIR"]
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "emapp.log"

    handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    handler.setLevel(app.config.get("LOG_LEVEL", "INFO"))

    app.logger.addHandler(handler)
    logging.getLogger().setLevel(app.config.get("LOG_LEVEL", "INFO"))
