"""Application entry point."""

import os

from config.settings import load_env_file

load_env_file()

from app import create_app
from config.settings import DevelopmentConfig, ProductionConfig, TestingConfig

config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

env = os.environ.get("FLASK_ENV", "development")
app = create_app(config_map.get(env, DevelopmentConfig))

if __name__ == "__main__":
    app.run(
        host=app.config.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", app.config.get("PORT", 50006))),
        debug=app.config.get("DEBUG", False),
    )
