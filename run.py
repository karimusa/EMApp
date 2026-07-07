"""Application entry point."""

import os

from app import create_app
from config.settings import DevelopmentConfig, ProductionConfig

config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}

env = os.environ.get("FLASK_ENV", "development")
app = create_app(config_map.get(env, DevelopmentConfig))

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
