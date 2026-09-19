$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "wslc-common.ps1")

Write-Host "=== Containers ==="
Get-WslcOutput -Arguments @("container", "list", "--all")

Write-Host "`n=== Rede agenda-network ==="
Get-WslcOutput -Arguments @("network", "list")

Write-Host "`n=== Volumes ==="
Get-WslcOutput -Arguments @("volume", "list")
