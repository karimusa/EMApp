# Build Roadmap

## Completed

- Frozen enterprise UI (templates, CSS, JS, navigation)
- SQL repository layer (`app/db/repositories/*`) with mock fallback
- `/api/v1/*` JSON contracts
- `setup.ps1` + `start.bat` for Windows deployment (port 50006)
- `scripts/seed_database.py` + `docs/planning/sql/seed.sql`
- `scripts/verify_live_reads.py` — confirm read layer per screen

## Live SQL deployment

1. Copy project to target path (e.g. `G:\EM` on SDAZ001MLD21)
2. Run `start.bat` (or `setup.ps1 -PrepareOnly` then `python run.py`)
3. Configure `.env` with **bootstrap** credentials only (`BOOTSTRAP_*`)
4. Deploy `docs/planning/sql/schema.sql`
5. Configure `scripts/seed.env` from `scripts/seed.env.example` and run `python scripts/seed_database.py`
6. Set `DATA_SOURCE=sql` (or `auto`) and run `python scripts/verify_live_reads.py`
7. Confirm screens: login, dashboard, run-history, agent-jobs, logs, users, monitoring, validation, settings

`.env` bootstraps MonthEndOrchestrationDB. All runtime server/database names come
from **orchestration.app_connections** only.

## Not yet wired (next phase)

- Run / Validate / Start New Run (stored procedures)
- Admin user CRUD mutations
- Reports page (Coming Soon — Phase 2)

Design references: `docs/planning/sql/`
