# RRA Month-End Orchestration (EMApp)

Enterprise month-end orchestration console. UI is frozen; data loads through
`app/dashboard/data.py` (SQL repositories with mock fallback for offline/testing).

## First run (Windows — e.g. `G:\EM` on `SDAZ001MLD21`)

1. **Copy the configuration template**

   ```powershell
   cd G:\EM
   copy .env.example .env
   ```

2. **Edit `.env`** and fill in:

   | Variable | Example |
   |----------|---------|
   | `BOOTSTRAP_SERVER` | `SDAZ001MLD21` |
   | `BOOTSTRAP_DATABASE` | `MonthEndOrchestrationDB` |
   | `BOOTSTRAP_USER` | `MonthEndApp` |
   | `BOOTSTRAP_PASSWORD` | your real SQL password |
   | `CONNECTION_SECRET_KEY` | your real Fernet key |

   `.env` contains **only the bootstrap connection** — the server that hosts
   `MonthEndOrchestrationDB`. All runtime SQL connections are loaded from
   `orchestration.app_connections` after bootstrap succeeds.

3. **Test bootstrap and registry load**

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup.ps1 -TestConnection
   ```

   Confirm you see:

   ```text
   Bootstrap connection: SUCCESS
   Runtime registry loaded successfully.
   ```

4. **Deploy schema and seed** (first-time database setup)

   - Deploy `docs/planning/sql/schema.sql`
   - Fill `SEED_*` in `.env` (or `scripts\seed.env`) and run `python scripts\seed_database.py`

5. **Start the app**

   ```bat
   start.bat
   ```

   Open **http://127.0.0.1:50006/login**

| User   | Password  | Role     |
|--------|-----------|----------|
| admin  | admin123  | Admin    |
| viewer | viewer123 | ReadOnly |

## Quick start (after first run)

```bat
start.bat
```

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

- `BOOTSTRAP_SERVER` — server hosting `MonthEndOrchestrationDB` (e.g. `SDAZ001MLD21`)
- `BOOTSTRAP_DATABASE`, `BOOTSTRAP_USER`, `BOOTSTRAP_PASSWORD`

That bootstrap connection reaches `MonthEndOrchestrationDB` so the app can execute:

```sql
SELECT * FROM orchestration.app_connections WHERE is_active = 1;
```

No other runtime server names belong in `.env`.

### Runtime connections (database only)

After bootstrap succeeds, every operational SQL connection (`PRIMARY`, `REMOTE_SQL`, etc.)
is loaded from `orchestration.app_connections`. Connection strings are built
dynamically by `ConnectionManager`; repositories are the only layer that uses them.

### Seed variables (`SEED_*`)

`SEED_*` in `.env` are used **only** by `scripts/seed_database.py` to insert initial
rows into `orchestration.app_connections`. The running application does not read them.

## Offline / testing

```bash
pytest                          # mock fallback tests
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
