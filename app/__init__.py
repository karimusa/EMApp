"""EMApp - Emergency Management Application."""

from flask import Flask

from config.settings import Config


def create_app(config_class=Config):
    """Application factory pattern."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)

    from app.routes.main import main_bp

    app.register_blueprint(main_bp)

    return app
