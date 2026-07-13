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

function Write-DevCommandOutput {
    param(
        [Parameter(ValueFromPipeline = $true)]
        $Record
    )

    process {
        if ($Record -is [System.Management.Automation.ErrorRecord]) {
            $message = if ($Record.Exception) { $Record.Exception.Message } else { "$Record" }
            if ($message) {
                Write-Host $message
            }
        } elseif ($null -ne $Record) {
            Write-Host $Record
        }
    }
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
        & $FilePath @Arguments 2>&1 | Write-DevCommandOutput

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

function Invoke-DevGitCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$StepName,

        [switch]$NonFatal
    )

    $previousNativeErrorPref = $null
    if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -Scope Global -ErrorAction SilentlyContinue) {
        $previousNativeErrorPref = $PSNativeCommandUseErrorActionPreference
        $PSNativeCommandUseErrorActionPreference = $false
    }

    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'

    try {
        & git @Arguments 2>&1 | Write-DevCommandOutput

        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) {
            $exitCode = 0
        }

        if ($exitCode -ne 0) {
            if ($NonFatal) {
                Write-Host ('  WARNING: {0} failed with exit code {1}. Continuing.' -f $StepName, $exitCode) -ForegroundColor Yellow
                return $false
            }
            throw ('{0} failed with exit code {1}' -f $StepName, $exitCode)
        }

        return $true
    } finally {
        $ErrorActionPreference = $previousErrorAction
        if ($null -ne $previousNativeErrorPref) {
            $PSNativeCommandUseErrorActionPreference = $previousNativeErrorPref
        }
    }
}

function ConvertTo-ProcessArgumentsString {
    param(
        [Parameter(ValueFromPipeline = $true)]
        [string[]]$Arguments
    )

    $quoted = foreach ($argument in $Arguments) {
        if ($null -eq $argument) {
            continue
        }
        if ($argument -match '[\s"]') {
            '"' + ($argument.Replace('"', '\"')) + '"'
        } else {
            $argument
        }
    }

    return ($quoted -join ' ')
}

function Write-DevProcessLine {
    param(
        [string]$Line
    )

    if ($null -ne $Line -and $Line.Length -gt 0) {
        Write-Host $Line
    }
}

function Invoke-DevForegroundCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @(),

        [string]$WorkingDirectory = '',

        [int]$ReadyPort = 0,

        [scriptblock]$OnPortReady = $null,

        [int]$ReadyTimeoutSeconds = 60
    )

    if (-not (Test-Path -LiteralPath $FilePath)) {
        throw ('Executable was not found: {0}' -f $FilePath)
    }

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = ConvertTo-ProcessArgumentsString -Arguments $Arguments
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    if ($WorkingDirectory) {
        $startInfo.WorkingDirectory = $WorkingDirectory
    }

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    $process.EnableRaisingEvents = $true

    $outputHandler = [System.Diagnostics.DataReceivedEventHandler] {
        param($sender, $eventArgs)
        if ($eventArgs.Data) {
            Write-DevProcessLine -Line $eventArgs.Data
        }
    }

    $null = $process.add_OutputDataReceived($outputHandler)
    $null = $process.add_ErrorDataReceived($outputHandler)

    if (-not $process.Start()) {
        throw ('Failed to start process: {0}' -f $FilePath)
    }

    $process.BeginOutputReadLine()
    $process.BeginErrorReadLine()

    $portReady = $false
    $portSignaled = $false
    $readyDeadline = $null
    if ($ReadyPort -gt 0) {
        $readyDeadline = (Get-Date).AddSeconds($ReadyTimeoutSeconds)
    }

    try {
        while (-not $process.HasExited) {
            if ($ReadyPort -gt 0 -and -not $portSignaled) {
                if (Test-AppPortListening -Port $ReadyPort) {
                    $portReady = $true
                    $portSignaled = $true
                    if ($OnPortReady) {
                        & $OnPortReady
                    }
                } elseif ($readyDeadline -and (Get-Date) -gt $readyDeadline) {
                    throw ('Process did not listen on port {0} within {1} seconds.' -f $ReadyPort, $ReadyTimeoutSeconds)
                }
            }

            Start-Sleep -Milliseconds 200
        }

        $process.WaitForExit()
        Start-Sleep -Milliseconds 150

        $exitCode = $process.ExitCode
        if ($null -eq $exitCode) {
            $exitCode = 0
        }

        if ($ReadyPort -gt 0 -and -not $portReady -and $exitCode -eq 0) {
            throw ('EMApp exited before port {0} became ready.' -f $ReadyPort)
        }

        return $exitCode
    } finally {
        if (-not $process.HasExited) {
            try {
                $process.Kill()
            } catch {
            }
        }
        $process.Dispose()
    }
}
