#Requires -Version 5.1
<#
.SYNOPSIS
    Prepare RRA Month-End Orchestration (EMApp) on Windows.

.DESCRIPTION
    Verifies Python, creates/reuses a virtual environment, installs Python packages,
    checks for the Microsoft ODBC Driver for SQL Server, loads .env configuration,
    and optionally tests the bootstrap database connection.

    Runtime server and database names are loaded from orchestration.app_connections
    after startup — they are not hardcoded in the application.

.PARAMETER PrepareOnly
    Install dependencies and exit without starting the app (used by start.bat).

.PARAMETER TestConnection
    Test bootstrap SQL connectivity and loaded app_connections, then exit.

.PARAMETER Port
    Application port (default 50006).

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 -PrepareOnly
    .\setup.ps1 -TestConnection
#>
param(
    [string]$ProjectRoot = "",
    [string]$VenvName = ".venv",
    [int]$Port = 50006,
    [switch]$PrepareOnly,
    [switch]$TestConnection,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host @"
EMApp setup — RRA Month-End Orchestration

Usage:
  .\setup.ps1 [-PrepareOnly] [-TestConnection] [-Port 50006]

  PrepareOnly     Install/check only; do not start the Flask app
  TestConnection  Verify bootstrap SQL + orchestration.app_connections
  Port            Default 50006 (EMApp; port 5000 is intentionally avoided)

Deploy path example:
  G:\EM on SDAZ001MLD21  ->  copy project to G:\EM, run start.bat
"@
}

function Find-Python311 {
    <#
    .SYNOPSIS
        Locate Python 3.11+ via py -3, python, or python3.
    #>
    $candidates = @(
        @{ Label = "py -3"; Exe = "py";     VenvArgs = @("-3") },
        @{ Label = "python";  Exe = "python";  VenvArgs = @() },
        @{ Label = "python3"; Exe = "python3"; VenvArgs = @() }
    )

    foreach ($candidate in $candidates) {
        try {
            $versionArgs = $candidate.VenvArgs + @("--version")
            $versionText = & $candidate.Exe @versionArgs 2>&1 | Out-String
            $versionText = $versionText.Trim()

            if ($versionText -match "Python 3\.(1[1-9]|[2-9]\d)") {
                return [PSCustomObject]@{
                    Label    = $candidate.Label
                    Exe      = $candidate.Exe
                    VenvArgs = $candidate.VenvArgs
                    Version  = $versionText
                }
            }
        } catch {
            # Try the next candidate.
        }
    }

    return $null
}

function New-VirtualEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Python,
        [Parameter(Mandatory = $true)]
        [string]$VenvPath
    )

    $venvArgs = $Python.VenvArgs + @("-m", "venv", $VenvPath)
    & $Python.Exe @venvArgs
}

function Test-SqlServerOdbcDriver {
    Write-Host "`n[4/6] Checking SQL Server ODBC driver..." -ForegroundColor Yellow

    try {
        $drivers = @(Get-OdbcDriver -Platform "64-bit" -ErrorAction Stop |
            Where-Object { $_.Name -like "*SQL Server*" })

        if ($drivers.Count -gt 0) {
            foreach ($driver in $drivers) {
                Write-Host "  Found: $($driver.Name)" -ForegroundColor Green
            }
            return
        }

        Write-Host "  WARNING: No SQL Server ODBC driver detected." -ForegroundColor Yellow
    } catch {
        Write-Host "  WARNING: Could not check ODBC drivers ($($_.Exception.Message))." -ForegroundColor Yellow
    }

    Write-Host "  Install 'ODBC Driver 18 for SQL Server' from Microsoft." -ForegroundColor Yellow
    Write-Host "  Mock/offline mode still works without the driver." -ForegroundColor Gray
}

function Import-DotEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvFilePath
    )

    Get-Content $EnvFilePath | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

if ($Help) { Show-Help; exit 0 }

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = $PSScriptRoot
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path

Write-Host "=== EMApp Setup ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"

# 1. Python 3.11+
Write-Host "`n[1/6] Checking Python..." -ForegroundColor Yellow
$python = Find-Python311
if (-not $python) {
    Write-Host "ERROR: Python 3.11+ is required." -ForegroundColor Red
    exit 1
}
Write-Host "  OK: $($python.Version) ($($python.Label))" -ForegroundColor Green

# 2. Virtual environment
Write-Host "`n[2/6] Virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $ProjectRoot $VenvName
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  Creating $venvPath"
    New-VirtualEnvironment -Python $python -VenvPath $venvPath
} else {
    Write-Host "  Reusing existing venv" -ForegroundColor Green
}

# 3. Python packages
Write-Host "`n[3/6] Installing Python packages..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
Write-Host "  Dependencies installed." -ForegroundColor Green

# 4. ODBC driver for SQL Server
Test-SqlServerOdbcDriver

# 5. Environment file
Write-Host "`n[5/6] Environment configuration..." -ForegroundColor Yellow
$envFile = Join-Path $ProjectRoot ".env"
$exampleEnv = Join-Path $ProjectRoot ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $exampleEnv)) {
    Copy-Item $exampleEnv $envFile
    Write-Host "  Created .env from .env.example — edit bootstrap credentials." -ForegroundColor Yellow
}
if (Test-Path $envFile) {
    Import-DotEnv -EnvFilePath $envFile
    Write-Host "  Loaded .env" -ForegroundColor Green
} else {
    Write-Host "  No .env file — app will use mock data (DATA_SOURCE=auto)." -ForegroundColor Yellow
}

$env:PORT = "$Port"
$env:FLASK_ENV = if ($env:FLASK_ENV) { $env:FLASK_ENV } else { "development" }

# 6. Optional connection test
if ($TestConnection) {
    Write-Host "`n[6/6] Testing database connection..." -ForegroundColor Yellow
    $testScript = Join-Path $ProjectRoot "scripts\verify_live_reads.py"
    & $venvPython $testScript --connections-only
    exit $LASTEXITCODE
}

Write-Host "`n[6/6] Setup complete." -ForegroundColor Green
Write-Host "  Port: $Port" -ForegroundColor Cyan
Write-Host "  URL:  http://127.0.0.1:$Port/login" -ForegroundColor Cyan

if ($PrepareOnly) {
    Write-Host "  PrepareOnly — exiting without starting the app." -ForegroundColor Gray
    exit 0
}

Write-Host "`nStarting EMApp... Press Ctrl+C to stop.`n" -ForegroundColor Gray
Set-Location $ProjectRoot
& $venvPython (Join-Path $ProjectRoot "run.py")
