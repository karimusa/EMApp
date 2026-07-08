@echo off
REM EMApp launcher — place project in G:\EM on SDAZ001MLD21 and run this file.
setlocal
cd /d "%~dp0"

echo === EMApp start ===
echo Project: %CD%

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" -PrepareOnly -Port 50006
if errorlevel 1 (
    echo Setup failed.
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found after setup.
    exit /b 1
)

call ".venv\Scripts\activate.bat"
set PORT=50006
set FLASK_ENV=development

echo.
echo Starting EMApp on http://127.0.0.1:50006/login
echo Press Ctrl+C to stop.
echo.

python run.py
