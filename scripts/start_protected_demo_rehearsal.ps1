param(
    [int]$AppPort = 8877,
    [int]$ProxyPort = 8878,
    [string]$Principal = "clerk@example.gov",
    [string]$Roles = "clerk_admin,meeting_editor",
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    Split-Path -Parent $PSScriptRoot
}

function Write-RehearsalPlan {
    param(
        [string]$RepoRoot,
        [string]$UpstreamUrl,
        [string]$ProxyUrl
    )

    $appCommand = "python -m uvicorn civicclerk.main:app --host 127.0.0.1 --port $AppPort"
    $proxyCommand = "python scripts/local_trusted_header_proxy.py"

    Write-Output "Protected demo rehearsal profile"
    Write-Output "Repo root: $RepoRoot"
    Write-Output "App URL: $UpstreamUrl"
    Write-Output "Proxy URL: $ProxyUrl"
    Write-Output "Set CIVICCLERK_STAFF_AUTH_MODE=trusted_header"
    Write-Output "Set CIVICCLERK_STAFF_SSO_PROVIDER=local trusted-header rehearsal proxy"
    Write-Output "Set CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER=X-Staff-Email"
    Write-Output "Set CIVICCLERK_STAFF_SSO_ROLES_HEADER=X-Staff-Roles"
    Write-Output "Set CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES=127.0.0.1/32"
    Write-Output "Set CIVICCLERK_LOCAL_PROXY_UPSTREAM=$UpstreamUrl"
    Write-Output "Set CIVICCLERK_LOCAL_PROXY_LISTEN_HOST=127.0.0.1"
    Write-Output "Set CIVICCLERK_LOCAL_PROXY_LISTEN_PORT=$ProxyPort"
    Write-Output "Set CIVICCLERK_LOCAL_PROXY_PRINCIPAL=$Principal"
    Write-Output "Set CIVICCLERK_LOCAL_PROXY_ROLES=$Roles"
    Write-Output "App command: $appCommand"
    Write-Output "Proxy command: $proxyCommand"
    Write-Output "Smoke check: GET $UpstreamUrl/health"
    Write-Output "Readiness check: GET $UpstreamUrl/staff/auth-readiness"
    Write-Output "Browser check: open $ProxyUrl/staff"
    Write-Output "Stop both Python processes when the rehearsal ends."
}

$repoRoot = Get-RepoRoot
$upstreamUrl = "http://127.0.0.1:$AppPort"
$proxyUrl = "http://127.0.0.1:$ProxyPort"

$env:CIVICCLERK_STAFF_AUTH_MODE = "trusted_header"
$env:CIVICCLERK_STAFF_SSO_PROVIDER = "local trusted-header rehearsal proxy"
$env:CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER = "X-Staff-Email"
$env:CIVICCLERK_STAFF_SSO_ROLES_HEADER = "X-Staff-Roles"
$env:CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES = "127.0.0.1/32"
$env:CIVICCLERK_LOCAL_PROXY_UPSTREAM = $upstreamUrl
$env:CIVICCLERK_LOCAL_PROXY_LISTEN_HOST = "127.0.0.1"
$env:CIVICCLERK_LOCAL_PROXY_LISTEN_PORT = "$ProxyPort"
$env:CIVICCLERK_LOCAL_PROXY_PRINCIPAL = $Principal
$env:CIVICCLERK_LOCAL_PROXY_ROLES = $Roles

Write-RehearsalPlan -RepoRoot $repoRoot -UpstreamUrl $upstreamUrl -ProxyUrl $proxyUrl

if ($PrintOnly) {
    return
}

$appProcess = Start-Process python `
    -ArgumentList "-m", "uvicorn", "civicclerk.main:app", "--host", "127.0.0.1", "--port", "$AppPort" `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 3

$proxyProcess = Start-Process python `
    -ArgumentList "scripts/local_trusted_header_proxy.py" `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -PassThru

Write-Output "Started app PID: $($appProcess.Id)"
Write-Output "Started proxy PID: $($proxyProcess.Id)"
Write-Output "Browse $proxyUrl/staff to exercise the protected demo profile."
