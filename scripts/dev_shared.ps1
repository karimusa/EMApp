#Requires -Version 5.1
<#
.SYNOPSIS
    Shared helpers for dev.ps1 (Windows PowerShell 5.1 and PowerShell 7+).
#>

function Test-IsWindowsPlatform {
    try {
        if ($env:OS -eq 'Windows_NT') {
            return $true
        }
        if ($PSVersionTable.ContainsKey('PSEdition') -and $PSVersionTable.PSEdition -eq 'Desktop') {
            return $true
        }
        if ($PSVersionTable.ContainsKey('PSEdition') -and $PSVersionTable.PSEdition -eq 'Core') {
            $isWindowsVar = Get-Variable -Name IsWindows -ErrorAction SilentlyContinue
            if ($null -ne $isWindowsVar -and $isWindowsVar.Value) {
                return $true
            }
        }
        return $false
    } catch {
        return $false
    }
}

function Test-PathWritable {
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

function Test-ProjectPermissions {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    $targets = @(
        $ProjectRoot,
        (Join-Path $ProjectRoot '.git'),
        (Join-Path $ProjectRoot 'logs')
    )

    foreach ($target in $targets) {
        if (-not (Test-PathWritable -Path $target -ProjectRoot $ProjectRoot)) {
            return $false
        }
    }

    $fetchHead = Join-Path $ProjectRoot '.git\FETCH_HEAD'
    if (Test-Path -LiteralPath $fetchHead) {
        try {
            $stream = [System.IO.File]::Open(
                $fetchHead,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
            $stream.Close()
            $stream.Dispose()
        } catch {
            return $false
        }
    }

    return $true
}

function Invoke-DevPermissionRepair {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    $fixScript = Join-Path $ProjectRoot 'scripts\fix_permissions.ps1'
    if (-not (Test-Path -LiteralPath $fixScript)) {
        throw ('Permission repair script not found: {0}' -f $fixScript)
    }

    & $fixScript -ProjectRoot $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw ('Permission repair failed with exit code {0}' -f $LASTEXITCODE)
    }
}

function Test-AppPortListening {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
            $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -First 1
            return $null -ne $listener
        }
    } catch {
    }

    return $false
}

function Stop-ListenerOnPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $stopped = 0
    try {
        if (-not (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue)) {
            return $stopped
        }

        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($connection in $connections) {
            $processId = $connection.OwningProcess
            if ($processId -and $processId -gt 0) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                $stopped++
            }
        }
    } catch {
    }

    if ($stopped -gt 0) {
        Start-Sleep -Milliseconds 750
    }

    return $stopped
}

function Wait-AppPortReady {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port,

        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-AppPortListening -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 400
    }
    return $false
}

function Start-DevBrowser {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        Start-Process $Url | Out-Null
        return $true
    } catch {
        return $false
    }
}

function New-DevStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    return [pscustomobject]@{
        Name   = $Name
        Status = 'pending'
        Detail = ''
    }
}

function Set-DevStepStatus {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Step,

        [Parameter(Mandatory = $true)]
        [ValidateSet('ok', 'warn', 'skip', 'fail')]
        [string]$Status,

        [string]$Detail = ''
    )

    $Step.Status = $Status
    $Step.Detail = $Detail
}

function Get-DevStepSymbol {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Status
    )

    switch ($Status) {
        'ok' { return [char]0x2713 }
        'warn' { return '!' }
        'skip' { return '-' }
        'fail' { return 'x' }
        default { return '.' }
    }
}

function Write-DevHeader {
    Write-Host ''
    Write-Host '=========================' -ForegroundColor Cyan
    Write-Host 'EMApp Developer Startup' -ForegroundColor Cyan
    Write-Host '=========================' -ForegroundColor Cyan
    Write-Host ''
}

function Write-DevStepLine {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Step
    )

    $symbol = Get-DevStepSymbol -Status $step.Status
    $color = switch ($step.Status) {
        'ok' { 'Green' }
        'warn' { 'Yellow' }
        'skip' { 'DarkGray' }
        'fail' { 'Red' }
        default { 'Gray' }
    }
    $line = '{0} {1}' -f $symbol, $step.Name
    if ($step.Detail) {
        $line = '{0} ({1})' -f $line, $step.Detail
    }
    Write-Host $line -ForegroundColor $color
}

function Write-DevSummary {
    param(
        [Parameter(Mandatory = $true)]
        [array]$Steps
    )

    Write-Host ''
    foreach ($step in $Steps) {
        $symbol = Get-DevStepSymbol -Status $step.Status
        $color = switch ($step.Status) {
            'ok' { 'Green' }
            'warn' { 'Yellow' }
            'skip' { 'DarkGray' }
            'fail' { 'Red' }
            default { 'Gray' }
        }
        $line = '{0} {1}' -f $symbol, $step.Name
        if ($step.Detail) {
            $line = '{0} ({1})' -f $line, $step.Detail
        }
        Write-Host $line -ForegroundColor $color
    }
    Write-Host ''
}

function Invoke-DevNativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @(),

        [Parameter(Mandatory = $true)]
        [string]$StepName
    )

    $previousNativeErrorPref = $null
    if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue) {
        $previousNativeErrorPref = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
    }

    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'

    try {
        & $FilePath @Arguments 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                $message = if ($_.Exception) { $_.Exception.Message } else { "$_" }
                if ($message) {
                    Write-Host $message
                }
            } else {
                Write-Host $_
            }
        }

        if ($LASTEXITCODE -ne 0) {
            throw ('{0} failed with exit code {1}' -f $StepName, $LASTEXITCODE)
        }
    } finally {
        $ErrorActionPreference = $previousErrorAction
        if ($null -ne $previousNativeErrorPref) {
            $PSNativeCommandUseErrorActionPreference = $previousNativeErrorPref
        }
    }
}
