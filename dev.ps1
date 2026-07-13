#Requires -Version 5.1
<#
.SYNOPSIS
    One-command Windows development startup for EMApp.

.DESCRIPTION
    Development-only workflow: permissions, git fetch/pull, venv, packages,
    setup, database check, stop old server, start app, open browser.

.EXAMPLE
    .\dev.ps1

.EXAMPLE
    .\dev.ps1 -Branch cursor/dashboard-execution-2c1b

.EXAMPLE
    VS Code: Ctrl+Shift+B  (task: EMApp: Run Development)
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$VenvName = '.venv',
    [int]$Port = 50006,
    [string]$Branch = '',
    [switch]$SkipGitPull,
    [switch]$NoBrowser,
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$DevStartupBuildId = 'dev-process-startup-2026-07-13'

. (Join-Path $PSScriptRoot 'scripts\dev_shared.ps1')

function Show-DevHelp {
    Write-Host @'
EMApp development startup (Windows)

Usage:
  .\dev.ps1 [-Branch cursor/dashboard-execution-2c1b] [-SkipGitPull] [-NoBrowser] [-Port 50006]

  Branch        git fetch origin and checkout this branch before pull
  SkipGitPull   Do not run git fetch/pull
  NoBrowser     Do not open http://127.0.0.1:50006 automatically
  Port          Default 50006

Examples:
  .\dev.ps1
  .\dev.ps1 -Branch cursor/dashboard-execution-2c1b

VS Code:
  Ctrl+Shift+B  ->  EMApp: Run Development
'@
}

if ($Help) {
    Show-DevHelp
    exit 0
}

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
}

$ProjectRoot = (Resolve-Path -Path $ProjectRoot).Path
$setupScript = Join-Path $ProjectRoot 'setup.ps1'
$runScript = Join-Path $ProjectRoot 'run.py'
$venvPython = Join-Path $ProjectRoot (Join-Path $VenvName 'Scripts\python.exe')
$deployCheckScript = Join-Path $ProjectRoot 'scripts\verify_deployed_code.py'
$verifyScript = Join-Path $ProjectRoot 'scripts\verify_live_reads.py'
$appUrl = 'http://127.0.0.1:{0}' -f $Port

if (-not (Test-Path -LiteralPath $setupScript)) {
    throw ('setup.ps1 was not found at {0}' -f $setupScript)
}
if (-not (Test-Path -LiteralPath $runScript)) {
    throw ('run.py was not found at {0}' -f $runScript)
}

$steps = @(
    (New-DevStep -Name 'Permissions'),
    (New-DevStep -Name 'Git'),
    (New-DevStep -Name 'Virtual Environment'),
    (New-DevStep -Name 'Python Packages'),
    (New-DevStep -Name 'Setup'),
    (New-DevStep -Name 'Database'),
    (New-DevStep -Name 'Stopped old server'),
    (New-DevStep -Name 'Started EMApp'),
    (New-DevStep -Name 'Browser opened')
)

Write-DevHeader
Write-Host ('Project: {0}' -f $ProjectRoot) -ForegroundColor Gray
Write-Host ('Build:   {0}' -f $DevStartupBuildId) -ForegroundColor Gray
Write-Host ('URL:     {0}/login' -f $appUrl) -ForegroundColor Gray
if ($Branch) {
    Write-Host ('Branch:  {0}' -f $Branch) -ForegroundColor Gray
}
Write-Host ''

# Stop any running EMApp instance before permission/git work (releases port and repo locks).
$preStopCount = 0
if (Test-IsWindowsPlatform) {
    $preStopCount = Stop-ListenerOnPort -Port $Port
    if ($preStopCount -gt 0) {
        Write-Host ('Stopped {0} process(es) on port {1} before sync.' -f $preStopCount, $Port) -ForegroundColor Gray
        Write-Host ''
    }
}

# 1. Permissions (automatic, non-interactive)
$permStep = $steps[0]
try {
    if (-not (Test-IsWindowsPlatform)) {
        Set-DevStepStatus -Step $permStep -Status 'skip' -Detail 'not Windows'
    } elseif (Test-ProjectPermissions -ProjectRoot $ProjectRoot) {
        Set-DevStepStatus -Step $permStep -Status 'ok' -Detail 'already writable'
    } elseif (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'scripts\fix_permissions.ps1'))) {
        Set-DevStepStatus -Step $permStep -Status 'warn' -Detail 'repair script unavailable'
        Write-Host '  WARNING: Permission issues detected but fix_permissions.ps1 is not present.' -ForegroundColor Yellow
    } else {
        Write-Host '[1/9] Repairing Windows permissions...' -ForegroundColor Yellow
        Invoke-DevPermissionRepair -ProjectRoot $ProjectRoot -Port $Port
        if (-not (Test-ProjectPermissions -ProjectRoot $ProjectRoot)) {
            throw 'Permission repair completed but .git is still not writable. Run scripts\diagnose_repo_permissions.ps1 and repair from an elevated PowerShell session.'
        }
        Set-DevStepStatus -Step $permStep -Status 'ok' -Detail 'repaired'
    }
} catch {
    Set-DevStepStatus -Step $permStep -Status 'warn' -Detail $_.Exception.Message
    Write-Host ('  Permission repair skipped: {0}' -f $_.Exception.Message) -ForegroundColor Yellow
}
Write-DevStepLine -Step $permStep

# 2. Git fetch / checkout / pull (optional)
$gitStep = $steps[1]
if ($SkipGitPull) {
    Set-DevStepStatus -Step $gitStep -Status 'skip' -Detail 'SkipGitPull'
} elseif (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Set-DevStepStatus -Step $gitStep -Status 'skip' -Detail 'git not installed'
} elseif (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot '.git'))) {
    Set-DevStepStatus -Step $gitStep -Status 'skip' -Detail 'not a git repo'
} else {
    Write-Host '[2/9] Syncing latest code...' -ForegroundColor Yellow
    Push-Location -Path $ProjectRoot
    try {
        if (-not (Test-ProjectPermissions -ProjectRoot $ProjectRoot)) {
            Write-Host '  WARNING: .git is not writable. Attempting permission repair before git sync...' -ForegroundColor Yellow
            Invoke-DevPermissionRepair -ProjectRoot $ProjectRoot -Port $Port
        }

        $gitIssues = @()

        if (-not (Invoke-DevGitCommand -Arguments @('fetch', 'origin') -StepName 'git fetch' -NonFatal)) {
            $gitIssues += 'fetch failed'
            if (-not (Test-ProjectPermissions -ProjectRoot $ProjectRoot)) {
                Write-Host '  WARNING: git fetch failed and .git is still not writable (ACL/lock issue, not a code error).' -ForegroundColor Yellow
                Write-Host '  Run: .\scripts\diagnose_repo_permissions.ps1' -ForegroundColor Yellow
                Write-Host '  Then: .\scripts\fix_permissions.ps1  (elevated PowerShell if needed)' -ForegroundColor Yellow
            }
        }

        if ($Branch) {
            if (-not (Invoke-DevGitCommand -Arguments @('checkout', $Branch) -StepName 'git checkout' -NonFatal)) {
                $gitIssues += 'checkout failed'
            }
        }

        if (-not (Invoke-DevGitCommand -Arguments @('pull', '--ff-only') -StepName 'git pull' -NonFatal)) {
            $gitIssues += 'pull failed'
        }

        if ($gitIssues.Count -eq 0) {
            if ($Branch) {
                Set-DevStepStatus -Step $gitStep -Status 'ok' -Detail $Branch
            } else {
                Set-DevStepStatus -Step $gitStep -Status 'ok'
            }
        } else {
            Set-DevStepStatus -Step $gitStep -Status 'warn' -Detail ($gitIssues -join '; ')
            Write-Host '  WARNING: Git sync had issues. Continuing with local code.' -ForegroundColor Yellow
        }
    } catch {
        Set-DevStepStatus -Step $gitStep -Status 'warn' -Detail $_.Exception.Message
        Write-Host ('  WARNING: git sync failed: {0}' -f $_.Exception.Message) -ForegroundColor Yellow
        Write-Host '  Continuing with local code.' -ForegroundColor Gray
    } finally {
        Pop-Location
    }
}
Write-DevStepLine -Step $gitStep

# 3-5. Virtual environment, packages, and setup via setup.ps1 -PrepareOnly
$venvStep = $steps[2]
$packagesStep = $steps[3]
$setupStep = $steps[4]

Write-Host '[3-5/9] Running setup (venv, packages, environment)...' -ForegroundColor Yellow
try {
    Invoke-DevNativeCommand -FilePath 'powershell.exe' -Arguments @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', $setupScript,
        '-PrepareOnly',
        '-ProjectRoot', $ProjectRoot,
        '-VenvName', $VenvName,
        '-Port', "$Port"
    ) -StepName 'setup.ps1 -PrepareOnly'

    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw ('Virtual environment python.exe was not created at {0}' -f $venvPython)
    }

    Set-DevStepStatus -Step $venvStep -Status 'ok'
    Set-DevStepStatus -Step $packagesStep -Status 'ok'
    Set-DevStepStatus -Step $setupStep -Status 'ok'
    Write-DevStepLine -Step $venvStep
    Write-DevStepLine -Step $packagesStep
    Write-DevStepLine -Step $setupStep
} catch {
    Set-DevStepStatus -Step $venvStep -Status 'fail' -Detail $_.Exception.Message
    Set-DevStepStatus -Step $packagesStep -Status 'fail'
    Set-DevStepStatus -Step $setupStep -Status 'fail'
    Write-DevSummary -Steps $steps
    throw
}

# 6. Database verification (continue on warning — mock mode still works)
$dbStep = $steps[5]
Write-Host '[6/9] Verifying database connection...' -ForegroundColor Yellow
try {
    if (-not (Test-Path -LiteralPath $deployCheckScript)) {
        throw 'verify_deployed_code.py not found'
    }
    if (-not (Test-Path -LiteralPath $verifyScript)) {
        throw 'verify_live_reads.py not found'
    }

    Invoke-DevNativeCommand -FilePath $venvPython -Arguments @($deployCheckScript) -StepName 'Verify deployed code'
    Invoke-DevNativeCommand -FilePath $venvPython -Arguments @($verifyScript, '--connections-only') -StepName 'Test database connection'
    Set-DevStepStatus -Step $dbStep -Status 'ok'
} catch {
    Set-DevStepStatus -Step $dbStep -Status 'warn' -Detail 'mock mode available'
    Write-Host ('  WARNING: Database check failed: {0}' -f $_.Exception.Message) -ForegroundColor Yellow
    Write-Host '  The app will start in mock mode if PRIMARY is unavailable.' -ForegroundColor Gray
}
Write-DevStepLine -Step $dbStep

# 7. Stop old server on port 50006
$stopStep = $steps[6]
Write-Host ('[7/9] Stopping any process listening on port {0}...' -f $Port) -ForegroundColor Yellow
$stoppedCount = Stop-ListenerOnPort -Port $Port
if ($stoppedCount -gt 0) {
    Set-DevStepStatus -Step $stopStep -Status 'ok' -Detail ('stopped {0} process(es)' -f $stoppedCount)
} else {
    Set-DevStepStatus -Step $stopStep -Status 'ok' -Detail 'port was free'
}
Write-DevStepLine -Step $stopStep

# 8-9. Start app and open browser
$startStep = $steps[7]
$browserStep = $steps[8]

Write-Host '[8/9] Starting EMApp...' -ForegroundColor Yellow
Write-Host '      Press Ctrl+C to stop.' -ForegroundColor Gray
Write-Host ''

$env:PORT = "$Port"
if (-not $env:FLASK_ENV) {
    $env:FLASK_ENV = 'development'
}

Set-Location -Path $ProjectRoot

$browserOpened = $false
$appStarted = $false

try {
    $exitCode = Invoke-DevForegroundCommand `
        -FilePath $venvPython `
        -Arguments @($runScript) `
        -WorkingDirectory $ProjectRoot `
        -ReadyPort $Port `
        -ReadyTimeoutSeconds 60 `
        -OnPortReady {
            $script:appStarted = $true
            Set-DevStepStatus -Step $startStep -Status 'ok'
            Write-DevStepLine -Step $startStep
            Write-Host ''
            Write-Host ('EMApp is running at {0}/login' -f $appUrl) -ForegroundColor Green
            Write-Host 'Press Ctrl+C to stop.' -ForegroundColor Gray
            Write-Host ''
            if (-not $NoBrowser) {
                $script:browserOpened = Start-DevBrowser -Url $appUrl
            }
        }

    if (-not $appStarted) {
        throw ('EMApp exited before port {0} was ready (exit code {1}).' -f $Port, $exitCode)
    }
    if ($exitCode -ne 0) {
        throw ('EMApp exited with code {0}' -f $exitCode)
    }
} catch {
    Set-DevStepStatus -Step $startStep -Status 'fail' -Detail $_.Exception.Message
    Set-DevStepStatus -Step $browserStep -Status 'skip'
    Write-DevSummary -Steps $steps
    throw
}

if ($NoBrowser) {
    Set-DevStepStatus -Step $browserStep -Status 'skip' -Detail 'NoBrowser'
} elseif ($browserOpened) {
    Set-DevStepStatus -Step $browserStep -Status 'ok' -Detail $appUrl
} else {
    Set-DevStepStatus -Step $browserStep -Status 'warn' -Detail 'open manually'
}
Write-DevStepLine -Step $browserStep

Write-DevSummary -Steps $steps
if ($appStarted) {
    Write-Host 'Stopped.' -ForegroundColor Gray
}
Write-Host ''
