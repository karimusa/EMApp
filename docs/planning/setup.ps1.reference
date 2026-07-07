#Requires -Version 5.1
<#
.SYNOPSIS
    Bootstrap script for RRA Month-End Orchestration web app.

.DESCRIPTION
    Verifies Python, creates/reuses a virtual environment, installs dependencies,
    optionally validates database connectivity, and starts the app on port 50006.

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 -SkipInstall
    .\setup.ps1 -TestConnection
#>
param(
    [string]$ProjectRoot = $PSScriptRoot,
    [string]$VenvName = ".venv",
    [int]$Port = 50006,
    [switch]$SkipInstall,
    [switch]$TestConnection,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host @"
RRA Month-End Orchestration — Setup Script

Usage:
  .\setup.ps1 [-ProjectRoot <path>] [-Port 50006] [-SkipInstall] [-TestConnection]

Options:
  -ProjectRoot     Path to EMApp project root (default: script directory parent)
  -VenvName        Virtual environment folder name (default: .venv)
  -Port            Application port (default: 50006)
  -SkipInstall     Skip pip install if venv already exists
  -TestConnection  Test bootstrap SQL connection and exit
  -Help            Show this help
"@
}

if ($Help) { Show-Help; exit 0 }

# Resolve project root (script lives in scripts/)
if ($ProjectRoot -eq $PSScriptRoot) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}

Write-Host "=== RRA Month-End Orchestration Setup ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"

# 1. Verify Python 3.11+
Write-Host "`n[1/5] Checking Python..." -ForegroundColor Yellow
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
  try {
    $version = & $cmd --version 2>&1
    if ($version -match "Python 3\.(1[1-9]|[2-9]\d)") {
      $pythonCmd = $cmd
      break
    }
  } catch {}
}

if (-not $pythonCmd) {
  Write-Host "ERROR: Python 3.11+ is required but not found." -ForegroundColor Red
  Write-Host "Install from https://www.python.org/downloads/" -ForegroundColor Red
  exit 1
}
Write-Host "  Found: $(& $pythonCmd --version)" -ForegroundColor Green

# 2. Create or reuse virtual environment
Write-Host "`n[2/5] Virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $ProjectRoot $VenvName
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
  Write-Host "  Creating venv at $venvPath"
  & $pythonCmd -m venv $venvPath
} else {
  Write-Host "  Reusing existing venv" -ForegroundColor Green
}

# 3. Install requirements
Write-Host "`n[3/5] Installing dependencies..." -ForegroundColor Yellow
if (-not $SkipInstall) {
  & $venvPython -m pip install --upgrade pip --quiet
  & $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
  Write-Host "  Dependencies installed." -ForegroundColor Green
} else {
  Write-Host "  Skipped (-SkipInstall)" -ForegroundColor Gray
}

# 4. Load .env if present
Write-Host "`n[4/5] Environment configuration..." -ForegroundColor Yellow
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
      [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
  }
  Write-Host "  Loaded .env" -ForegroundColor Green
} else {
  $exampleEnv = Join-Path $ProjectRoot ".env.example"
  if (Test-Path $exampleEnv) {
    Write-Host "  No .env found. Copy .env.example to .env and configure bootstrap credentials." -ForegroundColor Yellow
  }
}

# Optional: test database connection
if ($TestConnection) {
  Write-Host "`n[TEST] Testing bootstrap SQL connection..." -ForegroundColor Yellow
  $testScript = @"
import os, sys
sys.path.insert(0, r'$ProjectRoot')
os.chdir(r'$ProjectRoot')
from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.db.connection_manager import init_connection_manager
app = create_app()
with app.app_context():
    cm = init_connection_manager(app)
    cm.reload()
    conns = cm.all_connections()
    print(f'Loaded {len(conns)} connection(s): {list(conns.keys())}')
"@
  & $venvPython -c $testScript
  exit $LASTEXITCODE
}

# 5. Start application
Write-Host "`n[5/5] Starting application on port $Port..." -ForegroundColor Yellow
$env:PORT = "$Port"
$env:FLASK_ENV = if ($env:FLASK_ENV) { $env:FLASK_ENV } else { "development" }

Set-Location $ProjectRoot
Write-Host "  http://localhost:$Port" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop.`n" -ForegroundColor Gray

& $venvPython (Join-Path $ProjectRoot "run.py")
