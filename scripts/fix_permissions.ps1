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
    [string]$ProjectRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

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

Write-Host ''
Write-Host 'Permission repair complete.' -ForegroundColor Green
Write-Host 'You can re-run this script safely at any time.' -ForegroundColor Gray
