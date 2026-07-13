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
2. Copy `.env.example` to `.env` and fill in `BOOTSTRAP_*` + `CONNECTION_SECRET_KEY`
3. Run `powershell -ExecutionPolicy Bypass -File .\setup.ps1 -TestConnection`
4. Confirm `Bootstrap connection: SUCCESS` and `Runtime registry loaded successfully.`
5. Deploy `docs/planning/sql/schema.sql`
6. Fill `SEED_*` in `.env` and run `python scripts/seed_database.py`
7. Run `start.bat` and verify all screens

`.env` = bootstrap only (`BOOTSTRAP_SERVER` hosts MonthEndOrchestrationDB).
Runtime server/database names come from **orchestration.app_connections** only.

## Not yet wired (next phase)

- Run / Validate / Start New Run / Stop Run / Run Sequence (stored procedures)
- Admin user CRUD mutations
- Reports page (Coming Soon — Phase 2)

Design references: `docs/planning/sql/`
