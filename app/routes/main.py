"""Main application routes."""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Render the home page."""
    return render_template("index.html")


@main_bp.route("/health")
def health():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "app": "EMApp"}, 200
