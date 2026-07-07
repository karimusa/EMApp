# RRA Month-End Orchestration

Enterprise web application for RRA month-end close orchestration. Login-first, role-based access, database-driven connections, and one-step-at-a-time execution with validation.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, Flask |
| Database | SQL Server via pyodbc |
| Auth | Session-based login, Admin / ReadOnly roles |
| Frontend | Bootstrap 5, jQuery, HTMX |
| Port | **50006** |

## Features

- **Login-first flow** — polished enterprise login, then orchestration dashboard
- **DB-driven connections** — reads active rows from `orchestration.app_connections` at startup (no hardcoded server/database in app logic)
- **MonthEndOrchestrationDB** as source of truth
- **Phase tabs** — PRE, MAIN, BI, DAY5, POST
- **Step cards** — run and validate one step at a time (Admin only)
- **SQL Agent jobs** — monitored jobs from SPUS001BDBEXT and SPAZ001EDM10
- **Administration** — user management (Admin only)
- **Portable setup** — single PowerShell bootstrap script

## Project Structure

```
EMApp/
├── app/
│   ├── auth/              # Session decorators
│   ├── db/                # Connection manager, repositories
│   └── routes/            # auth, dashboard, admin, jobs, api
├── templates/             # Jinja2 templates
├── static/                # CSS, JS
├── config/                # Settings
├── scripts/
│   ├── setup.ps1          # Windows bootstrap script
│   └── run_dev.py
├── tests/
├── logs/
├── data/
└── docs/sql/              # Schema & stored procedure reference
```

## Prerequisites

- Python 3.11+
- ODBC Driver 18 for SQL Server
- Access to MonthEndOrchestrationDB (bootstrap credentials)
- `CONNECTION_SECRET_KEY` for decrypting connection passwords

### Mock / offline development

Set `FLASK_ENV=testing` to run without SQL Server (mock data, test users `admin`/`admin123` and `viewer`/`viewer123`).

## Quick Start (Windows)

```powershell
git clone https://github.com/karimusa/EMApp.git
cd EMApp
copy .env.example .env
# Edit .env with bootstrap credentials and CONNECTION_SECRET_KEY

.\scripts\setup.ps1
```

The script verifies Python, creates `.venv`, installs dependencies, and starts the app on **http://localhost:50006**.

### Options

```powershell
.\scripts\setup.ps1 -TestConnection   # Validate DB connectivity only
.\scripts\setup.ps1 -SkipInstall        # Reuse existing venv
.\scripts\setup.ps1 -Port 50006
```

## Quick Start (Linux / macOS)

```bash
git clone https://github.com/karimusa/EMApp.git
cd EMApp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env

export FLASK_ENV=development
python run.py
# → http://localhost:50006
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PORT` | Application port (default: 50006) |
| `SECRET_KEY` | Flask session signing key |
| `BOOTSTRAP_SERVER` | SQL Server for initial connection |
| `BOOTSTRAP_DATABASE` | MonthEndOrchestrationDB |
| `BOOTSTRAP_USER` / `BOOTSTRAP_PASSWORD` | Bootstrap credentials |
| `BOOTSTRAP_DRIVER` | ODBC driver name |
| `CONNECTION_SECRET_KEY` | Fernet key for `password_encrypted` column |

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Database

Connections are loaded from `orchestration.app_connections`:

| connection_name | server | database |
|-----------------|--------|----------|
| PRIMARY | SPUS001BDBEXT | MonthEndOrchestrationDB |
| REMOTE_SQL | SPAZ001EDM10 | msdb |

Passwords are stored encrypted in `password_encrypted` (not as login hashes). See `docs/sql/schema.sql` and `docs/sql/stored_procedures.sql`.

## Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Run/validate steps, admin menu, logs, jobs |
| **ReadOnly** | Dashboard, logs, job history (no run/validate/admin) |

## Pages

| Path | Description |
|------|-------------|
| `/login` | Enterprise login |
| `/dashboard` | Orchestration console |
| `/jobs` | SQL Agent jobs (both servers) |
| `/admin/users` | User management (Admin) |

## API Endpoints

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/api/steps/<id>/execute` | Admin | Execute step via stored proc |
| POST | `/api/steps/<id>/validate` | Admin | Validate step via stored proc |
| GET | `/api/logs` | Any | Execution log |
| GET | `/api/metrics` | Any | Run metrics |
| GET | `/api/run-status` | Any | Current run header |

## Tests

```bash
FLASK_ENV=testing pytest
```

## Moving to a New Machine

1. Clone the repository
2. Install Python 3.11+ and ODBC Driver 18 for SQL Server
3. Copy `.env.example` → `.env` and set bootstrap credentials
4. Run `.\scripts\setup.ps1` (Windows) or manual venv + `pip install` (Linux)
5. Ensure `orchestration.app_connections` has active rows on the target SQL Server

No server names or database names are hardcoded in application code.

## License

Proprietary — All rights reserved.
