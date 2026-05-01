$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Split-Path -Parent (Split-Path -Parent $ScriptRoot)
$EnvPath = Join-Path $AppRoot ".env"

function Read-EnvValue {
    param(
        [string]$Name,
        [string]$Default
    )
    if (-not (Test-Path $EnvPath)) {
        return $Default
    }
    $match = Select-String -Path $EnvPath -Pattern "^$([regex]::Escape($Name))=(.+)$" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($match) {
        return $match.Matches[0].Groups[1].Value.Trim()
    }
    return $Default
}

Set-Location $AppRoot
if (-not (Test-Path $EnvPath)) {
    throw "CivicClerk has not been installed yet. Run the 'Install or Repair CivicClerk' shortcut first so .env and Docker volumes are prepared."
}

docker compose up -d
$webPort = Read-EnvValue -Name "CIVICCLERK_WEB_PORT" -Default "8080"
Start-Process "http://127.0.0.1:$webPort/"
