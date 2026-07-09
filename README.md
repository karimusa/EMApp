# RRA Month-End Orchestration (EMApp)

Enterprise month-end orchestration console. UI is frozen; data loads through
`app/dashboard/data.py` (SQL repositories with mock fallback for offline/testing).

## Development (Windows)

One command for day-to-day coding:

```powershell
.\dev.ps1
```

Or in VS Code: **Ctrl+Shift+B** (task: `EMApp: Run Development`).

`dev.ps1` automatically:

1. Repairs Windows permissions (only if needed)
2. Runs `git pull` (warns and continues on failure)
3. Creates `.venv` if missing
4. Installs/updates Python packages
5. Runs `setup.ps1 -PrepareOnly`
6. Verifies database connectivity (warns and continues if unavailable)
7. Stops any process on port **50006**
8. Starts EMApp
9. Opens `http://127.0.0.1:50006`

Options:

```powershell
.\dev.ps1 -SkipGitPull    # do not run git pull
.\dev.ps1 -NoBrowser      # do not open the browser automatically
```

## First run (Windows — e.g. `G:\EM` on `SDAZ001MLD21`)

1. **Pull and copy the configuration template** (if `.env` is missing or cannot be edited)

   ```powershell
   cd G:\EM
   git pull origin main
   copy .env.example .env
   ```

   `setup.ps1` also creates `.env` from `.env.example` automatically when `.env`
   is missing. An existing `.env` is never overwritten.

2. **Bootstrap values in `.env.example`** (production template):

   | Variable | Value |
   |----------|-------|
   | `BOOTSTRAP_SERVER` | `SDAZ001MLD21` |
   | `BOOTSTRAP_DATABASE` | `MonthEndOrchestrationDB` |
   | `BOOTSTRAP_USER` | `MonthEndApp` |
   | `BOOTSTRAP_PASSWORD` | `MonthEndApp` |

   `CONNECTION_SECRET_KEY` — required only when `sql_password_encrypted` is Fernet-encrypted in the database.

   `.env` contains **only the bootstrap connection**. Runtime SQL connections load from
   `orchestration.app_connections` after bootstrap succeeds.

   **Important:** `dbo.users.password_hash` is a one-way app login hash.
   `orchestration.app_connections.sql_password_encrypted` must store the **real SQL login
   password** (plain text for development) or Fernet ciphertext — never a SHA/bcrypt hash.

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
   - On existing databases, run `docs/planning/sql/migrations/001_add_sql_password_encrypted.sql`
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
| `scripts/encrypt_password.py` | Encrypt SQL login passwords for `sql_password_encrypted` |

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
