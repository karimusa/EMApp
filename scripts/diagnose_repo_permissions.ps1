#Requires -Version 5.1
<#
.SYNOPSIS
    Diagnose Windows ACL and file-lock issues blocking git in the EMApp repo.

.DESCRIPTION
    Read-only checks for G:\EM-style permission problems: write probes on .git
    paths, icacls summary, processes that may lock FETCH_HEAD, and stale lock files.
    Does not modify ACLs. Run scripts\fix_permissions.ps1 to repair.

.EXAMPLE
    .\scripts\diagnose_repo_permissions.ps1 -ProjectRoot G:\EM
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [int]$Port = 50006
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $PSScriptRoot
}

$ProjectRoot = (Resolve-Path -Path $ProjectRoot).Path
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$gitDir = Join-Path $ProjectRoot '.git'

Write-Host '=== EMApp Repo Permission Diagnostics ===' -ForegroundColor Cyan
Write-Host ('Project: {0}' -f $ProjectRoot)
Write-Host ('User:    {0}' -f $CurrentUser)
Write-Host ''

function Test-PathWriteProbe {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return [PSCustomObject]@{ Path = $Path; Writable = $false; Detail = 'missing' }
    }

    $isDirectory = (Get-Item -LiteralPath $Path).PSIsContainer
    $probeName = '.emapp_diag_probe_{0}' -f ([guid]::NewGuid().ToString('N'))
    $probePath = if ($isDirectory) { Join-Path $Path $probeName } else {
        Join-Path (Split-Path -Parent $Path) $probeName
    }

    try {
        if ($isDirectory) {
            [System.IO.File]::WriteAllText($probePath, 'ok')
            Remove-Item -LiteralPath $probePath -Force -ErrorAction Stop
        } else {
            $stream = [System.IO.File]::Open(
                $Path,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
            $stream.Close()
            $stream.Dispose()
        }
        return [PSCustomObject]@{ Path = $Path; Writable = $true; Detail = 'ok' }
    } catch {
        return [PSCustomObject]@{ Path = $Path; Writable = $false; Detail = $_.Exception.Message }
    }
}

$probeTargets = @(
    $ProjectRoot,
    $gitDir,
    (Join-Path $gitDir 'FETCH_HEAD'),
    (Join-Path $gitDir 'logs'),
    (Join-Path $gitDir 'logs\HEAD'),
    (Join-Path $gitDir 'index'),
    (Join-Path $gitDir 'objects'),
    (Join-Path $gitDir 'refs'),
    (Join-Path $ProjectRoot 'logs')
)

Write-Host 'Write probes:' -ForegroundColor Yellow
$failed = @()
foreach ($target in $probeTargets) {
    $result = Test-PathWriteProbe -Path $target
    $color = if ($result.Writable) { 'Green' } else { 'Red' }
    $status = if ($result.Writable) { 'OK' } else { 'FAIL' }
    Write-Host ('  [{0}] {1}' -f $status, $result.Path) -ForegroundColor $color
    if (-not $result.Writable) {
        Write-Host ('        {0}' -f $result.Detail) -ForegroundColor DarkGray
        $failed += $result.Path
    }
}
Write-Host ''

Write-Host 'ACL summary (icacls):' -ForegroundColor Yellow
foreach ($target in @($ProjectRoot, $gitDir)) {
    if (Test-Path -LiteralPath $target) {
        Write-Host ('--- {0} ---' -f $target) -ForegroundColor Gray
        & icacls.exe $target 2>&1 | ForEach-Object { Write-Host $_ }
        Write-Host ''
    }
}

Write-Host 'Lock files:' -ForegroundColor Yellow
$lockCandidates = @(
    (Join-Path $gitDir 'index.lock'),
    (Join-Path $gitDir 'HEAD.lock'),
    (Join-Path $gitDir 'shallow.lock'),
    (Join-Path $gitDir 'packed-refs.lock')
)
foreach ($lockPath in $lockCandidates) {
    if (Test-Path -LiteralPath $lockPath) {
        Write-Host ('  PRESENT: {0}' -f $lockPath) -ForegroundColor Red
    }
}
Write-Host ''

Write-Host 'Processes that may lock the repo:' -ForegroundColor Yellow
try {
    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($listener in $listeners) {
            $proc = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host ('  Port {0}: PID {1} {2}' -f $Port, $proc.Id, $proc.ProcessName) -ForegroundColor Yellow
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
        Write-Host ('  PID {0}: {1}' -f $_.ProcessId, $_.ExecutablePath) -ForegroundColor Yellow
    }

Get-Process git, python, Code -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host ('  {0} PID {1}' -f $_.ProcessName, $_.Id) -ForegroundColor DarkGray
    }
Write-Host ''

if ($failed.Count -gt 0) {
    Write-Host 'RESULT: Git will fail until ACL/write access is repaired.' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Repair (run PowerShell as Administrator):' -ForegroundColor Cyan
    Write-Host ('  cd {0}' -f $ProjectRoot)
    Write-Host '  # Stop app / close VS Code windows using this repo first'
    Write-Host '  Get-NetTCPConnection -LocalPort 50006 -State Listen -ErrorAction SilentlyContinue |'
    Write-Host '    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }'
    Write-Host '  .\scripts\fix_permissions.ps1'
    Write-Host '  git fetch origin'
    Write-Host '  git checkout cursor/users-admin-actions-2c1b'
    Write-Host '  git pull origin cursor/users-admin-actions-2c1b'
    exit 1
}

Write-Host 'RESULT: Write probes passed. If git still fails, check network/credentials.' -ForegroundColor Green
exit 0
