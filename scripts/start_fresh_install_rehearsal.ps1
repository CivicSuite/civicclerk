param(
    [string]$WheelPath = "dist/civicclerk-0.1.19-py3-none-any.whl",
    [string]$RehearsalRoot = ".fresh-install-rehearsal",
    [int]$AppPort = 8776,
    [switch]$KeepServer,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    Split-Path -Parent $PSScriptRoot
}

function Resolve-RehearsalPath {
    param(
        [string]$RepoRoot,
        [string]$PathValue
    )

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }

    return Join-Path $RepoRoot $PathValue
}

function Write-FreshInstallPlan {
    param(
        [string]$RepoRoot,
        [string]$ResolvedWheelPath,
        [string]$ResolvedRehearsalRoot,
        [string]$PythonPath,
        [string]$AppUrl
    )

    Write-Output "Fresh install rehearsal profile"
    Write-Output "Repo root: $RepoRoot"
    Write-Output "Wheel path: $ResolvedWheelPath"
    Write-Output "Rehearsal root: $ResolvedRehearsalRoot"
    Write-Output "Virtual environment: $ResolvedRehearsalRoot\.venv"
    Write-Output "Create venv: python -m venv $ResolvedRehearsalRoot\.venv"
    Write-Output "Upgrade pip: $PythonPath -m pip install --upgrade pip"
    Write-Output "Install wheel: $PythonPath -m pip install $ResolvedWheelPath"
    Write-Output "Set CIVICCLERK_STAFF_AUTH_MODE=open"
    Write-Output "App command: $PythonPath -m uvicorn civicclerk.main:app --host 127.0.0.1 --port $AppPort"
    Write-Output "Smoke check: GET $AppUrl/health"
    Write-Output "Readiness check: GET $AppUrl/staff/auth-readiness"
    Write-Output "Browser check: open $AppUrl/staff"
    Write-Output "Expected health: {`"status`":`"ok`",`"service`":`"civicclerk`",`"version`":`"0.1.19`",`"civiccore`":`"0.21.0`"}"
    Write-Output "If the wheel is missing, build it first with: python -m build"
    Write-Output "If port $AppPort is already in use, stop the existing process or rerun with -AppPort set to an available port."
    Write-Output "By default this helper stops the app after smoke checks; pass -KeepServer to keep it running."
}

function Invoke-JsonGet {
    param(
        [string]$Url
    )

    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
    return $response.Content | ConvertFrom-Json
}

function Test-LoopbackPortAvailable {
    param(
        [int]$Port
    )

    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $listener) {
            $listener.Stop()
        }
    }
}

$repoRoot = Get-RepoRoot
$resolvedWheelPath = Resolve-RehearsalPath -RepoRoot $repoRoot -PathValue $WheelPath
$resolvedRehearsalRoot = Resolve-RehearsalPath -RepoRoot $repoRoot -PathValue $RehearsalRoot
$venvPath = Join-Path $resolvedRehearsalRoot ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"
$appUrl = "http://127.0.0.1:$AppPort"

Write-FreshInstallPlan `
    -RepoRoot $repoRoot `
    -ResolvedWheelPath $resolvedWheelPath `
    -ResolvedRehearsalRoot $resolvedRehearsalRoot `
    -PythonPath $pythonPath `
    -AppUrl $appUrl

if ($PrintOnly) {
    return
}

if (-not (Test-Path -LiteralPath $resolvedWheelPath -PathType Leaf)) {
    throw "Fresh install rehearsal cannot find the wheel at '$resolvedWheelPath'. Build the release artifact first with 'python -m build', then rerun this helper."
}

if (-not (Test-LoopbackPortAvailable -Port $AppPort)) {
    throw "Fresh install rehearsal cannot use 127.0.0.1:$AppPort because the port is already in use. Stop the existing local process or rerun this helper with -AppPort set to an available port."
}

New-Item -ItemType Directory -Force -Path $resolvedRehearsalRoot | Out-Null
python -m venv $venvPath
& $pythonPath -m pip install --upgrade pip
& $pythonPath -m pip install $resolvedWheelPath

$env:CIVICCLERK_STAFF_AUTH_MODE = "open"
$appProcess = Start-Process $pythonPath `
    -ArgumentList "-m", "uvicorn", "civicclerk.main:app", "--host", "127.0.0.1", "--port", "$AppPort" `
    -WorkingDirectory $resolvedRehearsalRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    $health = $null
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        try {
            $health = Invoke-JsonGet -Url "$appUrl/health"
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    if ($null -eq $health) {
        throw "The installed CivicClerk app did not answer $appUrl/health within 20 seconds. Check the app process output and whether port $AppPort is already in use."
    }

    if ($health.status -ne "ok" -or $health.service -ne "civicclerk" -or $health.version -ne "0.1.19" -or $health.civiccore -ne "0.21.0") {
        throw "Unexpected /health response: $($health | ConvertTo-Json -Compress). Expected CivicClerk 0.1.19 with CivicCore 0.21.0."
    }

    $readiness = Invoke-JsonGet -Url "$appUrl/staff/auth-readiness"
    if ($readiness.mode -ne "open") {
        throw "Unexpected /staff/auth-readiness mode '$($readiness.mode)'. Expected 'open' for the fresh install rehearsal."
    }

    $staffResponse = Invoke-WebRequest -Uri "$appUrl/staff" -UseBasicParsing -TimeoutSec 10
    if ($staffResponse.StatusCode -ne 200 -or $staffResponse.Content -notmatch "CivicClerk") {
        throw "Unexpected /staff response. Expected HTTP 200 with the CivicClerk staff workflow shell."
    }

    Write-Output "Fresh install smoke checks passed."
    Write-Output "Verified $appUrl/health"
    Write-Output "Verified $appUrl/staff/auth-readiness"
    Write-Output "Verified $appUrl/staff"

    if ($KeepServer) {
        Write-Output "Keeping app running at $appUrl with PID $($appProcess.Id). Stop it manually when the rehearsal ends."
    }
} finally {
    if (-not $KeepServer -and $null -ne $appProcess -and -not $appProcess.HasExited) {
        Stop-Process -Id $appProcess.Id -Force
        Write-Output "Stopped fresh install rehearsal app PID: $($appProcess.Id)"
    }
}
