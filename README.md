# EMApp

**Emergency Management Application** — a modern Python web application built with Flask.

## Features

- Flask application factory pattern
- Modular route blueprints
- Environment-based configuration (development / production / testing)
- Health check endpoint for monitoring
- Static assets (CSS, JavaScript, images)
- Pytest test suite
- VS Code development configuration

## Prerequisites

- Python 3.10 or higher (3.12 recommended)
- Git
- pip

## Project Structure

```
EMApp/
├── app/                    # Application package
│   ├── __init__.py         # Application factory
│   └── routes/             # Route blueprints
├── templates/              # Jinja2 HTML templates
├── static/                 # Static assets
│   ├── css/
│   ├── js/
│   └── images/
├── config/                 # Configuration modules
├── scripts/                # Utility scripts
├── tests/                  # Test suite
├── logs/                   # Application logs (gitignored)
├── data/                   # Application data (gitignored)
├── docs/                   # Documentation
├── .vscode/                # VS Code settings
├── run.py                  # Application entry point
├── requirements.txt        # Python dependencies
└── .env.example            # Environment variable template
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/karimusa/EMApp.git
cd EMApp
```

### 2. Create and activate a virtual environment

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set a secure `SECRET_KEY` for production use.

## Running the Application

### Development server

```bash
# From project root (with venv activated)
python run.py
```

Or use the helper script:

```bash
python scripts/run_dev.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### Production server (Gunicorn)

```bash
export FLASK_ENV=production
gunicorn --bind 0.0.0.0:8000 "run:app"
```

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## API Endpoints

| Method | Path     | Description              |
|--------|----------|--------------------------|
| GET    | `/`      | Home page                |
| GET    | `/health`| Health check (JSON)      |

## VS Code

Open the project folder in VS Code. Recommended extensions are listed in `.vscode/extensions.json`. Use **Run and Debug** (F5) to launch the development server or run tests.

## License

Proprietary — All rights reserved.
