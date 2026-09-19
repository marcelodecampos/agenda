$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$EnvFile = Join-Path $ProjectRoot ".env"

function Import-DotEnv {
    if (-not (Test-Path $EnvFile)) {
        throw "Arquivo .env nao encontrado em $ProjectRoot. Copie .env.example para .env antes de continuar."
    }

    foreach ($line in Get-Content $EnvFile) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            $name = $Matches[1]
            $value = $Matches[2].Trim()
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

function Get-Setting {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [string] $Default
    )

    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $Default
    }
    return $value
}

function Invoke-Wslc {
    param([Parameter(Mandatory)] [string[]] $Arguments)

    & wslc @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "WSLC falhou (codigo $LASTEXITCODE): wslc $($Arguments -join ' ')"
    }
}

function Get-WslcOutput {
    param([Parameter(Mandatory)] [string[]] $Arguments)

    $output = & wslc @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "WSLC falhou (codigo $LASTEXITCODE): wslc $($Arguments -join ' ')"
    }
    return $output
}

function Test-WslcResource {
    param(
        [Parameter(Mandatory)] [ValidateSet("container", "network", "volume")] [string] $Kind,
        [Parameter(Mandatory)] [string] $Name
    )

    $arguments = @($Kind, "list")
    if ($Kind -eq "container") {
        $arguments += "--all"
    }
    $output = Get-WslcOutput -Arguments $arguments
    $text = $output -join "`n"
    return $text -match "(?m)(^|\s)$([regex]::Escape($Name))(\s|$)"
}

function Ensure-WslcNetwork {
    param([Parameter(Mandatory)] [string] $Name)

    if (-not (Test-WslcResource -Kind network -Name $Name)) {
        Invoke-Wslc -Arguments @("network", "create", $Name)
    }
}

function Ensure-WslcVolume {
    param([Parameter(Mandatory)] [string] $Name)

    if (-not (Test-WslcResource -Kind volume -Name $Name)) {
        Invoke-Wslc -Arguments @("volume", "create", $Name)
    }
}

function Test-WslcContainer {
    param([Parameter(Mandatory)] [string] $Name)

    return Test-WslcResource -Kind container -Name $Name
}

function Remove-WslcContainer {
    param([Parameter(Mandatory)] [string] $Name)

    if (Test-WslcContainer -Name $Name) {
        Invoke-Wslc -Arguments @("container", "stop", $Name)
        Invoke-Wslc -Arguments @("container", "remove", $Name)
    }
}

Import-DotEnv
