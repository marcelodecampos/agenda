$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "wslc-common.ps1")

foreach ($containerName in @("agenda-keycloak", "agenda-mailpit", "agenda-postgres")) {
    Remove-WslcContainer -Name $containerName
}

Write-Host "Containers WSLC removidos. Volumes e dados foram preservados."
