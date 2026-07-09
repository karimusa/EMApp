#Requires -Version 5.1
<#
.SYNOPSIS
    Windows platform detection helpers for setup.ps1 (PS 5.1 and PS 7+ compatible).
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
