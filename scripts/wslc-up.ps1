$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "wslc-common.ps1")

$networkName = "agenda-network"
$postgresContainer = "agenda-postgres"
$keycloakContainer = "agenda-keycloak"
$mailpitContainer = "agenda-mailpit"
$postgresVolume = "agenda_postgres_data"
$keycloakVolume = "agenda_keycloak_data"

$postgresDb = Get-Setting -Name "POSTGRES_DB" -Default "agenda"
$postgresUser = Get-Setting -Name "POSTGRES_USER" -Default "agenda"
$postgresPassword = Get-Setting -Name "POSTGRES_PASSWORD" -Default "agenda"
$postgresPort = Get-Setting -Name "POSTGRES_PORT" -Default "5432"
$keycloakAdmin = Get-Setting -Name "KEYCLOAK_ADMIN" -Default "admin"
$keycloakAdminPassword = Get-Setting -Name "KEYCLOAK_ADMIN_PASSWORD" -Default "admin"
$keycloakPort = Get-Setting -Name "KEYCLOAK_PORT" -Default "8080"

if ([string]::IsNullOrWhiteSpace($postgresPassword)) {
    throw "POSTGRES_PASSWORD precisa estar definido no .env."
}
if ([string]::IsNullOrWhiteSpace($keycloakAdminPassword)) {
    throw "KEYCLOAK_ADMIN_PASSWORD precisa estar definido no .env."
}

$initDirectory = (Resolve-Path (Join-Path $ProjectRoot "docker\postgres\init")).Path
$keycloakImportDirectory = (Resolve-Path (Join-Path $ProjectRoot "keycloak\import")).Path

Ensure-WslcNetwork -Name $networkName
Ensure-WslcVolume -Name $postgresVolume
Ensure-WslcVolume -Name $keycloakVolume

if (-not (Test-WslcContainer -Name $postgresContainer)) {
    Invoke-Wslc -Arguments @(
        "run", "--detach", "--name", $postgresContainer,
        "--network", $networkName,
        "--network-alias", "postgres",
        "--env", "POSTGRES_DB=$postgresDb",
        "--env", "POSTGRES_USER=$postgresUser",
        "--env", "POSTGRES_PASSWORD=$postgresPassword",
        "--publish", "${postgresPort}:5432",
        "--volume", "${postgresVolume}:/var/lib/postgresql",
        "--volume", "${initDirectory}:/docker-entrypoint-initdb.d:ro",
        "--health-cmd", "pg_isready -U $postgresUser -d $postgresDb",
        "--health-interval", "5s",
        "--health-timeout", "5s",
        "--health-retries", "10",
        "postgres:18-alpine"
    )
}

if (-not (Test-WslcContainer -Name $keycloakContainer)) {
    Invoke-Wslc -Arguments @(
        "run", "--detach", "--name", $keycloakContainer,
        "--network", $networkName,
        "--env", "KC_DB=postgres",
        "--env", "KC_DB_URL_HOST=postgres",
        "--env", "KC_DB_URL_DATABASE=keycloak",
        "--env", "KC_DB_USERNAME=keycloak",
        "--env", "KC_DB_PASSWORD=keycloak",
        "--env", "KC_BOOTSTRAP_ADMIN_USERNAME=$keycloakAdmin",
        "--env", "KC_BOOTSTRAP_ADMIN_PASSWORD=$keycloakAdminPassword",
        "--publish", "${keycloakPort}:8080",
        "--volume", "${keycloakVolume}:/opt/keycloak/data",
        "--volume", "${keycloakImportDirectory}:/opt/keycloak/data/import",
        "quay.io/keycloak/keycloak:26.3",
        "start-dev", "--import-realm"
    )
}

if (-not (Test-WslcContainer -Name $mailpitContainer)) {
    Invoke-Wslc -Arguments @(
        "run", "--detach", "--name", $mailpitContainer,
        "--network", $networkName,
        "--publish", "1025:1025", "--publish", "8025:8025",
        "axllent/mailpit:v1.27.8"
    )
}

Write-Host "Containers WSLC iniciados. Execute scripts/wslc-status.ps1 para verificar o estado."
