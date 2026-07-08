# RRA Month-End Orchestration (EMApp)

Enterprise month-end orchestration console. UI is frozen; data loads through
`app/dashboard/data.py` (SQL repositories with mock fallback for offline/testing).

## Quick start (Windows — e.g. G:\EM on SDAZ001MLD21)

```bat
start.bat
```

Open **http://127.0.0.1:50006/login**

| User   | Password  | Role     |
|--------|-----------|----------|
| admin  | admin123  | Admin    |
| viewer | viewer123 | ReadOnly |

## Setup scripts

| File | Purpose |
|------|---------|
| `setup.ps1` | Verify Python, create venv, install packages, check ODBC driver, load `.env` |
| `start.bat` | Run setup (prepare only) then start the app on port **50006** |
| `scripts/seed_database.py` | Seed all tables from registry + sample run data |
| `scripts/verify_live_reads.py` | Confirm live SQL read layer for every screen |
| `scripts/encrypt_password.py` | Encrypt connection passwords for `app_connections` |

## Database-driven configuration

### Bootstrap (`.env` only)

The running application reads **one** SQL target from `.env`:

- `BOOTSTRAP_SERVER` — where MonthEndOrchestrationDB lives (e.g. `SDAZ001MLD21`)
- `BOOTSTRAP_DATABASE`, `BOOTSTRAP_USER`, `BOOTSTRAP_PASSWORD`

That bootstrap connection is used solely to reach MonthEndOrchestrationDB and load
`orchestration.app_connections`. No other runtime server names belong in `.env`.

### Runtime connections (database only)

After bootstrap succeeds, every operational SQL connection (`PRIMARY`, `REMOTE_SQL`, etc.)
is loaded from `orchestration.app_connections`. Connection strings are built
dynamically by `ConnectionManager`; repositories are the only layer that uses them.

### Initial setup

1. Copy `.env.example` to `.env` and set bootstrap credentials
2. Deploy `docs/planning/sql/schema.sql`
3. Copy `scripts/seed.env.example` to `scripts/seed.env` and set seed targets
4. Run `python scripts/seed_database.py` (writes `orchestration.app_connections`)
5. Set `DATA_SOURCE=sql` (or `auto` with bootstrap set) and restart
6. Run `python scripts/verify_live_reads.py`

Server and database names for operational work live in the database table —
never duplicated in `.env`.

## Offline / testing

```bash
pytest                          # 59 tests, mock fallback
python scripts/verify_live_reads.py   # mock read checks without SQL Server
```

## Project layout

```
EMApp/
├── app/                  # Flask app, auth, dashboard services, SQL repositories
├── templates/            # Frozen UI templates
├── static/               # Frozen CSS/JS
├── scripts/              # seed, verify, encrypt utilities
├── docs/planning/sql/    # schema.sql, seed.sql, stored_procedures.sql
├── setup.ps1             # Windows setup
├── start.bat             # Windows launcher
├── run.py                # Application entry point (port 50006)
└── requirements.txt
```

## API

`GET /api/v1/*` — JSON contracts mirror HTML view models (unchanged).

See [docs/ROADMAP.md](docs/ROADMAP.md) for the live SQL integration status.
