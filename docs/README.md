# EMApp Documentation

## SQL Reference

- [schema.sql](sql/schema.sql) — table definitions for `dbo.users` and `orchestration.*`
- [stored_procedures.sql](sql/stored_procedures.sql) — procedure contracts for execution, validation, and SQL Agent jobs

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup.ps1` | Windows bootstrap — venv, install, run on port 50006 |
| `scripts/run_dev.py` | Development server launcher |
| `scripts/encrypt_password.py` | Encrypt connection passwords for `app_connections` |

## Architecture

1. **Bootstrap** — env vars connect to MonthEndOrchestrationDB once
2. **Load connections** — read `orchestration.app_connections` (PRIMARY, REMOTE_SQL)
3. **Runtime** — all queries use loaded connections; no hardcoded servers
4. **Auth** — `dbo.users` with werkzeug password hashes; roles Admin / ReadOnly
5. **Orchestration** — dashboard driven by `orchestration.job_steps`; execute/validate via stored procs
