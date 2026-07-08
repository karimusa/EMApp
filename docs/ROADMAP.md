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

## Next — Live SQL Server integration

1. **Connection loading** — bootstrap env vars → `orchestration.app_connections`
2. **Repository layer** — swap `mock_data` for pyodbc/SQLAlchemy reads
3. **Step execution** — Admin Run/Validate via stored procedures
4. **Live refresh** — agent jobs, logs, monitoring telemetry
5. **User mutations** — CRUD on `dbo.users`
6. **Reports** — Phase 2 executive exports

Design references: `docs/planning/sql/`
