param(
    [string]$RehearsalRoot = ".docker-backup-restore-rehearsal",
    [string]$RunId = "",
    [switch]$Strict,
    [switch]$PrintOnly,
    [switch]$KeepRestoreDatabase
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonScript = Join-Path $RepoRoot "scripts\check_docker_backup_restore_rehearsal.py"
if (-not $RunId) {
    $RunId = Get-Date -Format "yyyyMMdd-HHmmss"
    $RunId = "run-$RunId"
}

$ArgsList = @($PythonScript, "--rehearsal-root", $RehearsalRoot, "--run-id", $RunId)
if ($Strict) {
    $ArgsList += "--strict"
}
if ($PrintOnly) {
    $ArgsList += "--print-only"
}
if ($KeepRestoreDatabase) {
    $ArgsList += "--keep-restore-database"
}

Write-Host "CivicClerk Docker/PostgreSQL backup/restore rehearsal profile"
Write-Host "Rehearsal root: $RehearsalRoot"
Write-Host "Run id: $RunId"
Write-Host "Python verifier: python scripts/check_docker_backup_restore_rehearsal.py"
Write-Host "Backup dump: backup\civicclerk-postgres.dump"
Write-Host "Backup manifest: backup\civicclerk-docker-backup-manifest.json"
Write-Host "Restore target: temporary PostgreSQL database civicclerk_restore_$($RunId -replace '[^a-zA-Z0-9_]', '_')"
Write-Host "Verification: pg_dump, pg_restore, restored application table list, manifest checksum"
Write-Host "Safety: the source civicclerk database is not dropped or overwritten."
Write-Host "Fix path: if the run fails, confirm Docker Desktop is running, start the stack with docker compose up -d, inspect docker compose logs postgres api, then rerun with a new -RunId."

Push-Location $RepoRoot
try {
    & python @ArgsList
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
