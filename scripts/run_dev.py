#!/usr/bin/env python3
"""Development server launcher — port 50006."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("PORT", "50006")

from run import app  # noqa: E402

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 50006)),
        debug=True,
    )
