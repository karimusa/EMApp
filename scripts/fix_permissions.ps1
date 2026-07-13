#Requires -Version 5.1
<#
.SYNOPSIS
    Repair Windows ACL/ownership on the EMApp project folder.

.DESCRIPTION
    Idempotent repair for fresh clones where git or logging fails with
    "Permission denied". Takes ownership, enables inheritance, and grants
    Full Control to the current user and the local Administrators group.
    Never grants Everyone Full Control.

.PARAMETER ProjectRoot
    Project root directory. Defaults to the parent of the scripts folder.
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [int]$Port = 50006,
    [switch]$SkipProcessStop
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Test-WriteAccess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        if ($Path -eq (Join-Path $ProjectRoot 'logs')) {
            try {
                New-Item -ItemType Directory -Path $Path -Force | Out-Null
            } catch {
                return $false
            }
        } elseif ($Path -eq (Join-Path $ProjectRoot '.git')) {
            return $false
        } else {
            try {
                New-Item -ItemType Directory -Path $Path -Force | Out-Null
            } catch {
                return $false
            }
        }
    }

    $probeName = '.emapp_write_probe_{0}' -f ([guid]::NewGuid().ToString('N'))
    $probePath = Join-Path -Path $Path -ChildPath $probeName

    try {
        [System.IO.File]::WriteAllText($probePath, 'ok')
        Remove-Item -LiteralPath $probePath -Force -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Test-RepairWriteAccess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    $gitDir = Join-Path $ProjectRoot '.git'
    $targets = @(
        @{ Label = 'project root'; Path = $ProjectRoot },
        @{ Label = '.git'; Path = $gitDir },
        @{ Label = '.git\FETCH_HEAD'; Path = (Join-Path $gitDir 'FETCH_HEAD') },
        @{ Label = '.git\logs'; Path = (Join-Path $gitDir 'logs') },
        @{ Label = '.git\logs\HEAD'; Path = (Join-Path $gitDir 'logs\HEAD') },
        @{ Label = '.git\index'; Path = (Join-Path $gitDir 'index') },
        @{ Label = '.git\objects'; Path = (Join-Path $gitDir 'objects') },
        @{ Label = '.git\refs'; Path = (Join-Path $gitDir 'refs') },
        @{ Label = 'logs'; Path = (Join-Path $ProjectRoot 'logs') }
    )

    return $targets | ForEach-Object {
        [PSCustomObject]@{
            Label = $_.Label
            Writable = (Test-WriteAccess -Path $_.Path -ProjectRoot $ProjectRoot)
        }
    }
}

function Stop-RepoLockingProcesses {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,

        [int]$Port = 50006
    )

    $stopped = 0

    try {
        if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
            $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            foreach ($connection in $connections) {
                $processId = $connection.OwningProcess
                if ($processId -and $processId -gt 0) {
                    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                    $stopped++
                }
            }
        }
    } catch {
    }

    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            $_.ExecutablePath.StartsWith($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            $stopped++
        }

    Get-Process git -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            $stopped++
        }

    if ($stopped -gt 0) {
        Start-Sleep -Milliseconds 750
    }

    return $stopped
}

function Clear-StaleGitLockFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    if (Get-Process git -ErrorAction SilentlyContinue) {
        return 0
    }

    $gitDir = Join-Path $ProjectRoot '.git'
    $lockNames = @('index.lock', 'HEAD.lock', 'shallow.lock', 'packed-refs.lock')
    $removed = 0

    foreach ($lockName in $lockNames) {
        $lockPath = Join-Path $gitDir $lockName
        if (Test-Path -LiteralPath $lockPath) {
            try {
                Remove-Item -LiteralPath $lockPath -Force -ErrorAction Stop
                Write-Host ('Removed stale lock: {0}' -f $lockPath) -ForegroundColor Gray
                $removed++
            } catch {
                Write-Host ('Could not remove lock: {0} ({1})' -f $lockPath, $_.Exception.Message) -ForegroundColor Yellow
            }
        }
    }

    return $removed
}

function Write-RepairVerificationResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,

        [Parameter(Mandatory = $true)]
        [string]$CurrentUser,

        [Parameter(Mandatory = $true)]
        [array]$Checks
    )

    Write-Host ''

    if ($Checks | Where-Object { -not $_.Writable }) {
        Write-Host 'Permission repair completed, but write access could not be verified.' -ForegroundColor Yellow
        Write-Host ''
        Write-Host 'Please rerun setup.ps1 from an elevated PowerShell session (Run as Administrator).' -ForegroundColor Yellow
        exit 1
    }

    Write-Host 'Permission repair completed successfully.' -ForegroundColor Green
    Write-Host ''
    Write-Host 'Current user:'
    Write-Host $CurrentUser
    Write-Host ''
    Write-Host 'Project:'
    Write-Host $ProjectRoot
    Write-Host ''
    Write-Host 'Verified writable:'
    foreach ($check in $Checks) {
        Write-Host ('OK {0}' -f $check.Label)
    }
}

function Invoke-AclCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$StepName
    )

    $output = & $FilePath @Arguments 2>&1
    if ($output) {
        $output | ForEach-Object { Write-Host $_ }
    }

    if ($LASTEXITCODE -ne 0) {
        throw ('{0} failed with exit code {1}' -f $StepName, $LASTEXITCODE)
    }
}

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}

$ProjectRoot = (Resolve-Path -Path $ProjectRoot).Path
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Write-Host '=== EMApp Windows Permission Repair ===' -ForegroundColor Cyan
Write-Host ('Project root: {0}' -f $ProjectRoot)
Write-Host ('Current user: {0}' -f $CurrentUser)
Write-Host ''

$logsDir = Join-Path $ProjectRoot 'logs'
if (-not (Test-Path -Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    Write-Host ('Created logs directory: {0}' -f $logsDir) -ForegroundColor Gray
}

if (-not $SkipProcessStop) {
    Write-Host 'Stopping processes that may lock the repo...' -ForegroundColor Yellow
    $stoppedCount = Stop-RepoLockingProcesses -ProjectRoot $ProjectRoot -Port $Port
    if ($stoppedCount -gt 0) {
        Write-Host ('Stopped {0} process(es). Close VS Code windows using this repo if git still fails.' -f $stoppedCount) -ForegroundColor Gray
    } else {
        Write-Host 'No EMApp/git processes needed stopping.' -ForegroundColor Gray
    }
    $null = Clear-StaleGitLockFiles -ProjectRoot $ProjectRoot
    Write-Host ''
}

Write-Host 'Taking ownership (takeown)...' -ForegroundColor Yellow
Invoke-AclCommand -FilePath 'takeown.exe' -Arguments @(
    '/F', $ProjectRoot,
    '/R',
    '/D', 'Y'
) -StepName 'takeown'

Write-Host 'Enabling inherited permissions (icacls)...' -ForegroundColor Yellow
Invoke-AclCommand -FilePath 'icacls.exe' -Arguments @(
    $ProjectRoot,
    '/inheritance:e'
) -StepName 'icacls inheritance'

Write-Host ('Granting Full Control to {0}...' -f $CurrentUser) -ForegroundColor Yellow
Invoke-AclCommand -FilePath 'icacls.exe' -Arguments @(
    $ProjectRoot,
    '/grant', "${CurrentUser}:(OI)(CI)F",
    '/T'
) -StepName 'icacls grant current user'

Write-Host 'Granting Full Control to Administrators...' -ForegroundColor Yellow
Invoke-AclCommand -FilePath 'icacls.exe' -Arguments @(
    $ProjectRoot,
    '/grant', 'Administrators:(OI)(CI)F',
    '/T'
) -StepName 'icacls grant Administrators'

$verificationChecks = Test-RepairWriteAccess -ProjectRoot $ProjectRoot
Write-RepairVerificationResult -ProjectRoot $ProjectRoot -CurrentUser $CurrentUser -Checks $verificationChecks
