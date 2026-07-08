@echo off
REM EMApp launcher — place project in G:\EM on SDAZ001MLD21 and run this file.
setlocal
cd /d "%~dp0"

set "PROJECT_ROOT=%~dp0"
set "VENV_PY=%PROJECT_ROOT%.venv\Scripts\python.exe"
set "PORT=50006"

echo === EMApp start ===
echo Project: %CD%

if not exist "%PROJECT_ROOT%setup.ps1" (
    echo setup.ps1 not found in %PROJECT_ROOT%
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%setup.ps1" -PrepareOnly -Port %PORT%
if errorlevel 1 (
    echo Setup failed.
    exit /b 1
)

if not exist "%VENV_PY%" (
    echo Virtual environment not found: %VENV_PY%
    exit /b 1
)

set FLASK_ENV=development

echo.
echo Starting EMApp on http://127.0.0.1:%PORT%/login
echo Press Ctrl+C to stop.
echo.

"%VENV_PY%" "%PROJECT_ROOT%run.py"
if errorlevel 1 (
    echo App exited with an error.
    exit /b 1
)

endlocal
