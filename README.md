# RRA Month-End Orchestration (EMApp)

Enterprise month-end orchestration console. UI is frozen; data loads through
`app/dashboard/data.py` (SQL repositories with mock fallback for offline/testing).

## First run (Windows — e.g. `G:\EM` on `SDAZ001MLD21`)

Fresh clone flow:

```text
Fresh clone
    ↓
setup.ps1
    ↓
permission repair (if needed)
    ↓
venv
    ↓
packages
    ↓
bootstrap verification
    ↓
run application
```

On Windows, `setup.ps1` checks whether the current user can write to the project
root, `.git`, and `logs`. If not (common after cloning to certain drives), it
offers to run `scripts\fix_permissions.ps1` automatically. You can also run
repair manually:

```powershell
cd G:\EM
powershell -ExecutionPolicy Bypass -File .\setup.ps1 -FixPermissions
```

1. **Pull and copy the configuration template** (if `.env` is missing or cannot be edited)

   ```powershell
   cd G:\EM
   git pull origin main
   copy .env.example .env
   ```

   Run `setup.ps1` first on a fresh clone so permission repair can run before
   `git pull` if ACL issues are present. `setup.ps1` also creates `.env` from
   `.env.example` automatically when `.env` is missing. An existing `.env` is
   never overwritten.

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
| `setup.ps1` | Verify Python, create venv, install packages, check ODBC driver, load `.env`; optional Windows permission repair |
| `scripts/fix_permissions.ps1` | Repair Windows ACL/ownership on the project folder (`takeown` + `icacls`) |
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
├── scripts/              # seed, verify, encrypt, fix_permissions utilities
├── docs/planning/sql/    # schema.sql, seed.sql, stored_procedures.sql
├── setup.ps1             # Windows setup
├── start.bat             # Windows launcher
├── run.py                # Application entry point (port 50006)
└── requirements.txt
```

## API

`GET /api/v1/*` — JSON contracts mirror HTML view models (unchanged).

See [docs/ROADMAP.md](docs/ROADMAP.md) for the live SQL integration status.
