param(
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvPath = Join-Path $Root ".env"
$TemplatePath = Join-Path $Root "docs\examples\docker.env.example"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command {
    param(
        [string]$Command,
        [string]$Fix
    )
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "$Command was not found. $Fix"
    }
}

function New-HexSecret {
    $bytes = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

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

function Wait-Http {
    param(
        [string]$Url,
        [string]$Name,
        [int]$Attempts = 45
    )
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 4
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                Write-Host "$Name is responding at $Url"
                return
            }
        } catch {
            if ($i -eq $Attempts) {
                throw "$Name did not respond at $Url. Run 'docker compose ps' and 'docker compose logs api frontend' from $Root for details."
            }
        }
        Start-Sleep -Seconds 3
    }
}

Set-Location $Root

Write-Host "CivicClerk Windows Install or Repair"
Write-Host "This starts the local Docker Compose product stack with seeded demo data by default."

Write-Step "Checking Docker Desktop prerequisites"
Require-Command -Command "docker" -Fix "Install Docker Desktop for Windows, start it, then rerun this installer."
docker --version | Write-Host
docker compose version | Write-Host
docker info *> $null

Write-Step "Preparing local environment file"
if (-not (Test-Path $TemplatePath)) {
    throw "Missing $TemplatePath. Reinstall or repair the CivicClerk package, then rerun this script."
}
if (-not (Test-Path $EnvPath)) {
    $secret = New-HexSecret
    $content = Get-Content $TemplatePath -Raw
    $content = $content -replace "CIVICCLERK_POSTGRES_PASSWORD=change-this-before-shared-use", "CIVICCLERK_POSTGRES_PASSWORD=$secret"
    Set-Content -Path $EnvPath -Value $content -Encoding UTF8
    Write-Host "Created .env from docs\examples\docker.env.example with a generated database password."
} else {
    Write-Host ".env already exists; preserving local settings."
}

$apiPort = Read-EnvValue -Name "CIVICCLERK_API_PORT" -Default "8776"
$webPort = Read-EnvValue -Name "CIVICCLERK_WEB_PORT" -Default "8080"
$seedMode = Read-EnvValue -Name "CIVICCLERK_DEMO_SEED" -Default "1"
$authMode = Read-EnvValue -Name "CIVICCLERK_STAFF_AUTH_MODE" -Default "open"

Write-Host "Staff auth mode: $authMode"
if ($authMode -eq "open") {
    Write-Host "Open staff auth is only for a single-workstation rehearsal. Use bearer or trusted_header before shared deployment." -ForegroundColor Yellow
}
Write-Host "Demo seed mode: $seedMode"

Write-Step "Building and starting CivicClerk"
docker compose up -d --build

Write-Step "Checking health endpoints"
Wait-Http -Url "http://127.0.0.1:$apiPort/health" -Name "CivicClerk API"
Wait-Http -Url "http://127.0.0.1:$webPort/" -Name "CivicClerk staff app"

Write-Host ""
Write-Host "CivicClerk is running."
Write-Host "Staff app: http://127.0.0.1:$webPort/"
Write-Host "API health: http://127.0.0.1:$apiPort/health"
Write-Host "Stop later with: docker compose down"

if (-not $NoOpen) {
    Start-Process "http://127.0.0.1:$webPort/"
}
