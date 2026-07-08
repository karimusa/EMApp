# Build Roadmap

## Completed — Production-ready UI (mock data)

- Enterprise login with loading, error, and validation states
- Operations console shell with consistent navigation
- Dashboard with phases, step cards, filters, modals
- Run History, Logs, Monitoring, Validation, Settings pages
- SQL Agent Jobs page (5 monitored jobs)
- Users admin page (Admin only)
- Reports page marked **Coming Soon — Phase 2**
- REST API (`/api/v1/*`) with data contracts matching `MonthEndOrchestrationDB`
- Admin vs ReadOnly permissions (execution controls hidden for ReadOnly)
- Mock data shaped like all 8 schema tables in `docs/planning/sql/schema.sql`

## Next — Live SQL Server (in progress)

Repositories in `app/db/repositories/` read MonthEndOrchestrationDB when `DATA_SOURCE=sql`
(or `DATA_SOURCE=auto` with bootstrap env vars set). Mock data remains the offline/test fallback.

1. Set bootstrap env vars in `.env` (see `.env.example`)
2. Deploy schema from `docs/planning/sql/schema.sql`
3. Seed `dbo.users`, `orchestration.app_connections`, `orchestration.job_steps`
4. Wire step execution via stored procedures (Run/Validate buttons)

## Later

- User mutations (CRUD on `dbo.users`)
- Reports — Phase 2 executive exports

Design references: `docs/planning/sql/`
