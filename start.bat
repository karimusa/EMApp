@echo off
REM EMApp launcher — delegates to dev.ps1 (one-command Windows workflow).
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
if errorlevel 1 (
    echo dev.ps1 failed.
    exit /b 1
)

endlocal
