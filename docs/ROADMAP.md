# Build Roadmap

## Completed

- Frozen enterprise UI (templates, CSS, JS, navigation)
- SQL repository layer (`app/db/repositories/*`) with mock fallback
- `/api/v1/*` JSON contracts
- `setup.ps1` + `start.bat` for Windows deployment (port 50006)
- `scripts/seed_database.py` + `docs/planning/sql/seed.sql`
- `scripts/verify_live_reads.py` — confirm read layer per screen

- Registry-based runtime connection resolution (`app/db/runtime_connections.py`)
- Job steps resolve logical targets (PRIMARY / REMOTE_SQL) from `orchestration.app_connections`

## Live SQL deployment

1. Copy project to target path (e.g. `G:\EM` on your SQL Server host)
2. Copy `.env.example` to `.env` and fill in `BOOTSTRAP_*` + `CONNECTION_SECRET_KEY`
3. Run `powershell -ExecutionPolicy Bypass -File .\setup.ps1 -TestConnection`
4. Confirm `Bootstrap connection: SUCCESS` and `Runtime registry loaded successfully.`
5. Deploy `docs/planning/sql/schema.sql` and `docs/planning/sql/migrations/002_add_job_steps_environment_name.sql`
6. Fill `SEED_*` in `.env` and run `python scripts/seed_database.py`
7. Run `start.bat` and verify all screens

`.env` = bootstrap only (`BOOTSTRAP_SERVER` hosts MonthEndOrchestrationDB).
Runtime server/database names come from **orchestration.app_connections** only.
Job steps declare logical targets (`environment_name`); physical hosts are never read from `job_steps.server_name` at runtime.

## Not yet wired (next phase)

- Run / Validate / Start New Run (stored procedures)
- Admin user CRUD mutations
- Reports page (Coming Soon — Phase 2)

Design references: `docs/planning/sql/`
