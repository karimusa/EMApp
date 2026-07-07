# RRA Month-End Orchestration — Incremental Build

Enterprise month-end orchestration web app. **We are in the design/build phase here** — nothing to clone or deploy locally until all steps are complete.

## Current step: 1 — Login page

### Run (design/testing)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:50006/login**

### Test users (mock, until database step)

| Username | Password   | Role     |
|----------|------------|----------|
| admin    | admin123   | Admin    |
| viewer   | viewer123  | ReadOnly |

### Tests

```bash
pytest
```

## Build roadmap

| Step | Feature                         | Status      |
|------|---------------------------------|-------------|
| 1    | Login page                      | **Current** |
| 2    | Dashboard layout                | Planned     |
| 3    | Connection loading from DB      | Planned     |
| 4    | Role-based screens              | Planned     |
| 5    | SQL Agent jobs page             | Planned     |
| 6    | Step execution                  | Planned     |
| 7    | Step validation                 | Planned     |
| 8    | Logs panel                      | Planned     |
| 9    | Metrics panel                   | Planned     |
| 10   | PowerShell bootstrap script     | Planned     |

See [docs/ROADMAP.md](docs/ROADMAP.md) for full design notes.

## Project structure (growing incrementally)

```
EMApp/
├── app/
│   ├── auth/           # Login service & decorators
│   └── routes/         # auth routes (login only for now)
├── templates/auth/     # Login templates
├── static/css/         # login.css
├── static/js/          # login.js
├── config/
├── tests/
└── docs/
```

When all steps are finished here, you can download the repository and deploy to your machine.
