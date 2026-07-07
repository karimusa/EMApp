"""SQL Agent jobs routes."""

from flask import Blueprint, render_template

from app.auth.decorators import login_required
from app.db.repositories.sql_agent import SqlAgentRepository

jobs_bp = Blueprint("jobs", __name__)
sql_agent_repo = SqlAgentRepository()


@jobs_bp.route("/jobs")
@login_required
def index():
    all_jobs = sql_agent_repo.get_all_jobs()
    servers = sorted({j.get("server_name", "Unknown") for j in all_jobs})
    jobs_by_server = {server: [j for j in all_jobs if j.get("server_name") == server] for server in servers}
    return render_template("jobs/index.html", jobs_by_server=jobs_by_server, servers=servers)
