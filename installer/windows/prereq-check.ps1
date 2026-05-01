$ErrorActionPreference = "Stop"

Write-Host "CivicClerk prerequisite check"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker was not found. Install Docker Desktop for Windows, start it, then rerun Install or Repair CivicClerk."
}

docker --version | Write-Host
docker compose version | Write-Host

try {
    docker info *> $null
} catch {
    throw "Docker Desktop is not running or this user cannot access Docker. Start Docker Desktop and wait until it reports 'Engine running'."
}

Write-Host "Prerequisites passed."
