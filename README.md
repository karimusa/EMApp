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

1. Set bootstrap credentials in `.env` (copy from `.env.example`)
2. Deploy `docs/planning/sql/schema.sql`
3. Seed: `python scripts/seed_database.py` (set `SEED_*` connection vars in `.env`)
4. Set `DATA_SOURCE=sql` and restart

At runtime the app loads **orchestration.app_connections** — server and database
names are never hardcoded in application code.

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
