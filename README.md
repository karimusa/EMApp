# RRA Month-End Orchestration

Enterprise month-end orchestration console for SQL Server. The UI reads through
`app/dashboard/data.py`, which delegates to SQL repositories when bootstrap
credentials are configured, or mock data otherwise.

## Run locally (mock — no SQL Server required)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:50006/login**

## Connect to MonthEndOrchestrationDB

Copy `.env.example` to `.env` and set:

```bash
DATA_SOURCE=sql
BOOTSTRAP_SERVER=SPUS001BDBEXT
BOOTSTRAP_DATABASE=MonthEndOrchestrationDB
BOOTSTRAP_USER=svc_orchestration
BOOTSTRAP_PASSWORD=...
CONNECTION_SECRET_KEY=...   # Fernet key for app_connections passwords
```

Deploy tables from `docs/planning/sql/schema.sql`, then seed users, connections,
and job steps. The app loads `orchestration.app_connections` on startup.

## Test users (mock `dbo.users`)

| Username | Password   | Role     |
|----------|------------|----------|
| admin    | admin123   | Admin    |
| viewer   | viewer123  | ReadOnly |

## Console pages

| Page | Route | Access |
|------|-------|--------|
| Dashboard | `/dashboard` | All signed-in users |
| Run History | `/run-history` | All signed-in users |
| SQL Agent Jobs | `/agent-jobs` | All signed-in users |
| Logs | `/logs` | All signed-in users |
| Monitoring | `/monitoring` | All signed-in users |
| Validation | `/validation` | All signed-in users |
| Reports | `/reports` | Coming Soon (Phase 2) |
| Settings | `/settings` | All signed-in users (read-only for ReadOnly role) |
| Users | `/admin/users` | Admin only |

## API (`/api/v1/*`)

JSON endpoints mirror the same view models as the HTML pages for live SQL integration:

- `GET /api/v1/health`
- `GET /api/v1/me`
- `GET /api/v1/dashboard`
- `GET /api/v1/run-history`
- `GET /api/v1/logs`
- `GET /api/v1/agent-jobs`
- `GET /api/v1/monitoring`
- `GET /api/v1/validation`
- `GET /api/v1/settings`
- `GET /api/v1/users` (Admin only)

## Tests

```bash
pytest
```

## Project structure

```
EMApp/
├── app/
│   ├── auth/              # Session auth, role decorators
│   ├── dashboard/         # View models + mock data contracts
│   └── routes/            # Pages + REST API
├── templates/             # Jinja2 console + login
├── static/                # CSS + JS
├── docs/planning/sql/     # Schema + stored procedures reference
└── tests/
```

See [docs/ROADMAP.md](docs/ROADMAP.md) for the live database integration plan.
