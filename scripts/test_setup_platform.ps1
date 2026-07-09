#Requires -Version 5.1
<#
.SYNOPSIS
    Verify Windows platform detection works on PowerShell 5.1 and 7+.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\test_setup_platform.ps1
    pwsh -File .\scripts\test_setup_platform.ps1
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'setup_platform.ps1')

$errors = @()

if ($PSVersionTable.ContainsKey('PSPlatform')) {
    Write-Host ('PSPlatform present: {0}' -f $PSVersionTable.PSPlatform) -ForegroundColor Gray
} else {
    Write-Host 'PSPlatform not present (expected on Windows PowerShell 5.1)' -ForegroundColor Gray
}

$detected = Test-IsWindowsPlatform
$edition = if ($PSVersionTable.ContainsKey('PSEdition')) { $PSVersionTable.PSEdition } else { '<none>' }
Write-Host ('PSEdition={0} OS={1} DetectedWindows={2}' -f $edition, $env:OS, $detected)

if ($env:OS -eq 'Windows_NT' -and -not $detected) {
    $errors += 'Expected DetectedWindows=True when OS=Windows_NT'
}

if ($PSVersionTable.ContainsKey('PSEdition') -and $PSVersionTable.PSEdition -eq 'Desktop' -and -not $detected) {
    $errors += 'Expected DetectedWindows=True on Windows PowerShell Desktop edition'
}

if ($errors.Count -gt 0) {
    Write-Host ''
    Write-Host 'FAILED:' -ForegroundColor Red
    foreach ($err in $errors) {
        Write-Host ('  - {0}' -f $err) -ForegroundColor Red
    }
    exit 1
}

Write-Host ''
Write-Host 'Windows platform detection OK.' -ForegroundColor Green
exit 0
