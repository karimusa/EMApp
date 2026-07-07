# AGENTS.md

## Cursor Cloud specific instructions

This is a single Python 3.12 / Flask app ("RRA Month-End Orchestration", internally `EMApp`). It is an incremental build currently at Step 1 (login page only); there is no database or external service — auth uses in-memory mock users in `app/auth/service.py`.

### Environment
- A virtualenv is created at `.venv` by the update script. Activate it before running anything: `. .venv/bin/activate`.
- Dependencies come from `requirements.txt`. `ruff` is not pinned there but is configured in `pyproject.toml`; the update script installs it into the venv.

### Run (dev)
- `python scripts/run_dev.py` — dev launcher, binds `0.0.0.0:50006`, `debug=True` (preferred for cloud/remote access).
- `python run.py` — binds `HOST`/`PORT` from env or `config/settings.py` defaults (`127.0.0.1:50006`).
- App URL: `http://127.0.0.1:50006/login`. Mock creds: `admin`/`admin123` (Admin), `viewer`/`viewer123` (ReadOnly).

### Test / Lint
- Tests: `pytest` (config in `pyproject.toml`, tests in `tests/`).
- Lint: `ruff check .`. Note: `run.py` intentionally has two `E402` violations because `load_dotenv()` must run before the app imports — this is pre-existing/expected, not a regression to "fix".
