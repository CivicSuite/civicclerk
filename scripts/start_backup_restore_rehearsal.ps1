param(
    [string]$RehearsalRoot = ".backup-restore-rehearsal",
    [string]$RunId = "",
    [switch]$Strict,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonScript = Join-Path $RepoRoot "scripts\check_backup_restore_rehearsal.py"
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

Write-Host "CivicClerk backup/restore rehearsal profile"
Write-Host "Rehearsal root: $RehearsalRoot"
Write-Host "Run id: $RunId"
Write-Host "Python verifier: python scripts/check_backup_restore_rehearsal.py"
Write-Host "Source stores: source-data\agenda-intake.db, source-data\agenda-items.db, source-data\meetings.db, source-data\packet-assembly.db, source-data\notice-checklist.db"
Write-Host "Backup manifest: backup\civicclerk-backup-manifest.json"
Write-Host "Restored stores: restored-data\*.db"
Write-Host "Restored export root: restored-exports"
Write-Host "Verification: database checksums, export checksums, restored agenda intake, agenda item, meeting, packet assembly, and notice checklist records"
Write-Host "Fix path: if the run fails, inspect the named file under $RehearsalRoot\$RunId, fix the backup source or env var, then rerun with a new -RunId."

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
