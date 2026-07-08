#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$VenvName = '.venv',
    [int]$Port = 50006,
    [switch]$PrepareOnly,
    [switch]$TestConnection,
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Show-Help {
    Write-Host @'
EMApp setup - RRA Month-End Orchestration

Usage:
  .\setup.ps1 [-PrepareOnly] [-TestConnection] [-Port 50006]

  PrepareOnly     Install/check only; do not start the Flask app
  TestConnection  Verify bootstrap SQL + orchestration.app_connections
  Port            Default 50006 (EMApp; port 5000 is intentionally avoided)

Deploy path example:
  G:\EM on SDAZ001MLD21  ->  copy project to G:\EM, run start.bat
'@
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @(),

        [Parameter(Mandatory = $true)]
        [string]$StepName
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ('{0} failed with exit code {1}' -f $StepName, $LASTEXITCODE)
    }
}

function Load-DotEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -Path $Path)) {
        return $false
    }

    foreach ($rawLine in Get-Content -Path $Path) {
        $line = $rawLine.Trim()

        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line.StartsWith('#')) { continue }

        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()

            if (
                (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                 ($value.StartsWith("'") -and $value.EndsWith("'"))) -and
                $value.Length -ge 2
            ) {
                $value = $value.Substring(1, $value.Length - 2)
            }

            [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }

    return $true
}

function Initialize-EnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvFilePath,

        [Parameter(Mandatory = $true)]
        [string]$ExampleEnvPath
    )

    if (Test-Path -Path $EnvFilePath) {
        Write-Host '  Found existing .env (not overwritten)' -ForegroundColor Green
        return
    }

    if (-not (Test-Path -Path $ExampleEnvPath)) {
        Write-Host '  WARNING: .env missing and .env.example was not found.' -ForegroundColor Yellow
        return
    }

    Copy-Item -Path $ExampleEnvPath -Destination $EnvFilePath
    Write-Host '  Created .env from .env.example' -ForegroundColor Yellow
    Write-Host '  Bootstrap values are pre-filled in the template.' -ForegroundColor Gray
}

function Test-BootstrapConfiguration {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvFilePath
    )

    $required = [ordered]@{
        BOOTSTRAP_SERVER   = 'Server hosting MonthEndOrchestrationDB (e.g. SDAZ001MLD21)'
        BOOTSTRAP_DATABASE = 'Bootstrap database name (e.g. MonthEndOrchestrationDB)'
        BOOTSTRAP_USER     = 'SQL login for bootstrap (e.g. MonthEndApp)'
        BOOTSTRAP_PASSWORD = 'SQL password for bootstrap login'
    }

    $missing = New-Object System.Collections.Generic.List[string]
    foreach ($entry in $required.GetEnumerator()) {
        $value = [System.Environment]::GetEnvironmentVariable($entry.Key, 'Process')
        if ([string]::IsNullOrWhiteSpace($value)) {
            $missing.Add(('{0} - {1}' -f $entry.Key, $entry.Value))
        }
    }

    if ($missing.Count -eq 0) {
        return
    }

    Write-Host ''
    Write-Host 'Bootstrap configuration is incomplete.' -ForegroundColor Red
    Write-Host ''
    Write-Host ('Edit: {0}' -f $EnvFilePath)
    Write-Host ''
    Write-Host 'Fill in these values:'
    foreach ($item in $missing) {
        Write-Host ('  {0}' -f $item)
    }
    Write-Host ''
    Write-Host 'Expected bootstrap template (.env.example):'
    Write-Host '  BOOTSTRAP_SERVER=SDAZ001MLD21'
    Write-Host '  BOOTSTRAP_DATABASE=MonthEndOrchestrationDB'
    Write-Host '  BOOTSTRAP_USER=MonthEndApp'
    Write-Host '  BOOTSTRAP_PASSWORD=MonthEndApp'
    Write-Host ''
    Write-Host 'If .env is missing or still blank, copy the template after git pull:'
    Write-Host '  copy .env.example .env'
    Write-Host ''
    Write-Host 'Runtime SQL connections come from orchestration.app_connections only.'
    Write-Host '.env stores the bootstrap connection only.'
    throw 'Bootstrap configuration is incomplete.'
}

function Get-PythonLauncher {
    $candidates = @(
        @{ FilePath = 'py';      Args = @('-3'); VersionArgs = @('-3', '--version'); DisplayName = 'py -3' },
        @{ FilePath = 'python';  Args = @();     VersionArgs = @('--version');       DisplayName = 'python' },
        @{ FilePath = 'python3'; Args = @();     VersionArgs = @('--version');       DisplayName = 'python3' }
    )

    foreach ($candidate in $candidates) {
        try {
            $version = & $candidate.FilePath @($candidate.VersionArgs) 2>&1 | Out-String
            if ($version -match 'Python 3\.(1[1-9]|[2-9]\d)') {
                return [pscustomobject]@{
                    FilePath    = $candidate.FilePath
                    Args        = $candidate.Args
                    DisplayName = $candidate.DisplayName
                    VersionText = $version.Trim()
                }
            }
        } catch {
        }
    }

    return $null
}

if ($Help) {
    Show-Help
    exit 0
}

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    if ($PSScriptRoot) {
        $ProjectRoot = $PSScriptRoot
    } else {
        $ProjectRoot = (Get-Location).Path
    }
}

$ProjectRoot = (Resolve-Path -Path $ProjectRoot).Path

Write-Host '=== EMApp Setup ===' -ForegroundColor Cyan
Write-Host ('Project root: {0}' -f $ProjectRoot)

$requirementsPath = Join-Path $ProjectRoot 'requirements.txt'
$envFile = Join-Path $ProjectRoot '.env'
$exampleEnv = Join-Path $ProjectRoot '.env.example'
$verifyScript = Join-Path $ProjectRoot 'scripts\verify_live_reads.py'
$runScript = Join-Path $ProjectRoot 'run.py'

if (-not (Test-Path -Path $requirementsPath)) {
    throw ('ERROR: requirements.txt was not found at {0}' -f $requirementsPath)
}
if (-not (Test-Path -Path $runScript)) {
    throw ('ERROR: run.py was not found at {0}' -f $runScript)
}

Write-Host ''
Write-Host '[1/6] Checking Python...' -ForegroundColor Yellow
$pythonLauncher = Get-PythonLauncher
if (-not $pythonLauncher) {
    throw 'ERROR: Python 3.11+ is required, but py/python/python3 was not found.'
}
Write-Host ('  OK: {0} | {1}' -f $pythonLauncher.DisplayName, $pythonLauncher.VersionText) -ForegroundColor Green

Write-Host ''
Write-Host '[2/6] Virtual environment...' -ForegroundColor Yellow
$venvPath = Join-Path $ProjectRoot $VenvName
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

if ((Test-Path -Path $venvPath) -and (-not (Test-Path -Path $venvPython))) {
    Write-Host '  WARNING: venv folder exists but python.exe is missing. Recreating...' -ForegroundColor Yellow
    Remove-Item -Path $venvPath -Recurse -Force
}

if (-not (Test-Path -Path $venvPython)) {
    Write-Host ('  Creating {0}' -f $venvPath)
    $venvArgs = @()
    if ($pythonLauncher.FilePath -eq 'py') {
        $venvArgs += $pythonLauncher.Args
    }
    $venvArgs += @('-m', 'venv', $venvPath)
    Invoke-NativeCommand -FilePath $pythonLauncher.FilePath -Arguments $venvArgs -StepName 'Create virtual environment'
} else {
    Write-Host '  Reusing existing venv' -ForegroundColor Green
}

if (-not (Test-Path -Path $venvPython)) {
    throw ('ERROR: Virtual environment python.exe was not created at {0}' -f $venvPython)
}

Write-Host ''
Write-Host '[3/6] Installing Python packages...' -ForegroundColor Yellow
Invoke-NativeCommand -FilePath $venvPython -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip', '--quiet') -StepName 'Upgrade pip'
Invoke-NativeCommand -FilePath $venvPython -Arguments @('-m', 'pip', 'install', '-r', $requirementsPath) -StepName 'Install requirements'
Write-Host '  Dependencies installed.' -ForegroundColor Green

Write-Host ''
Write-Host '[4/6] Checking SQL Server ODBC driver...' -ForegroundColor Yellow
try {
    if (Get-Command Get-OdbcDriver -ErrorAction SilentlyContinue) {
        $drivers = Get-OdbcDriver -Platform '64-bit' | Where-Object { $_.Name -like '*SQL Server*' }
        if ($drivers) {
            foreach ($driver in $drivers) {
                Write-Host ('  Found: {0}' -f $driver.Name) -ForegroundColor Green
            }
        } else {
            Write-Host '  WARNING: No SQL Server ODBC driver detected.' -ForegroundColor Yellow
            Write-Host "  Install 'ODBC Driver 18 for SQL Server' from Microsoft." -ForegroundColor Yellow
            Write-Host '  Mock/offline mode still works without the driver.' -ForegroundColor Gray
        }
    } else {
        Write-Host '  WARNING: Get-OdbcDriver is not available on this machine.' -ForegroundColor Yellow
        Write-Host '  You can still continue if the app is running in mock mode.' -ForegroundColor Gray
    }
} catch {
    Write-Host ('  WARNING: ODBC driver check could not be completed: {0}' -f $_.Exception.Message) -ForegroundColor Yellow
}

Write-Host ''
Write-Host '[5/6] Environment configuration...' -ForegroundColor Yellow
Initialize-EnvFile -EnvFilePath $envFile -ExampleEnvPath $exampleEnv

if (Test-Path -Path $envFile) {
    Load-DotEnv -Path $envFile | Out-Null
    Write-Host '  Loaded .env' -ForegroundColor Green
} else {
    Write-Host '  No .env file - app will use mock data (DATA_SOURCE=auto).' -ForegroundColor Yellow
}

$env:PORT = "$Port"
if (-not $env:FLASK_ENV) {
    $env:FLASK_ENV = 'development'
}

if ($TestConnection) {
    Test-BootstrapConfiguration -EnvFilePath $envFile
    Write-Host ''
    Write-Host '[6/6] Testing database connection...' -ForegroundColor Yellow
    if (-not (Test-Path -Path $verifyScript)) {
        throw ('ERROR: Connection test script not found at {0}' -f $verifyScript)
    }
    Invoke-NativeCommand -FilePath $venvPython -Arguments @($verifyScript, '--connections-only') -StepName 'Test database connection'
    exit 0
}

Write-Host ''
Write-Host '[6/6] Setup complete.' -ForegroundColor Green
Write-Host ('  Port: {0}' -f $Port) -ForegroundColor Cyan
Write-Host ('  URL:  http://127.0.0.1:{0}/login' -f $Port) -ForegroundColor Cyan

if ($PrepareOnly) {
    Write-Host '  PrepareOnly - exiting without starting the app.' -ForegroundColor Gray
    exit 0
}

Test-BootstrapConfiguration -EnvFilePath $envFile

Write-Host ''
Write-Host 'Starting EMApp... Press Ctrl+C to stop.'
Write-Host ''

Set-Location -Path $ProjectRoot
Invoke-NativeCommand -FilePath $venvPython -Arguments @($runScript) -StepName 'Start EMApp'
