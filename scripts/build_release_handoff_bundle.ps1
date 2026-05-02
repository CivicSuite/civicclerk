param(
    [string]$Version = "0.1.14",
    [string]$OutputPath = "",
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistRoot = Join-Path $RepoRoot "dist"
$WheelPath = Join-Path $DistRoot "civicclerk-$Version-py3-none-any.whl"
$SdistPath = Join-Path $DistRoot "civicclerk-$Version.tar.gz"
$ChecksumsPath = Join-Path $DistRoot "SHA256SUMS.txt"

if (-not $OutputPath) {
    $OutputPath = Join-Path $DistRoot "civicclerk-$Version-release-handoff.zip"
}

$BundleFiles = @(
    "README.md",
    "README.txt",
    "USER-MANUAL.md",
    "USER-MANUAL.txt",
    "CHANGELOG.md",
    "LICENSE",
    "docs/index.html",
    "docs/examples/deployment.env.example",
    "docs/examples/trusted-header-nginx.conf",
    "scripts/check_installer_readiness.py",
    "scripts/check_enterprise_installer_signing.py",
    "scripts/check_connector_sync_readiness.py",
    "scripts/run_mock_city_environment_suite.py",
    "scripts/check_vendor_live_sync_readiness.py",
    "scripts/run_connector_import_sync.py",
    "scripts/run_vendor_live_sync.py",
    "scripts/start_fresh_install_rehearsal.ps1",
    "scripts/start_fresh_install_rehearsal.sh",
    "scripts/check_backup_restore_rehearsal.py",
    "scripts/check_protected_deployment_smoke.py",
    "scripts/start_backup_restore_rehearsal.ps1",
    "scripts/start_backup_restore_rehearsal.sh",
    "scripts/start_protected_demo_rehearsal.ps1",
    "scripts/start_protected_demo_rehearsal.sh",
    "scripts/local_trusted_header_proxy.py",
    "dist/civicclerk-$Version-py3-none-any.whl",
    "dist/civicclerk-$Version.tar.gz",
    "dist/SHA256SUMS.txt"
)

Write-Host "CivicClerk release handoff bundle"
Write-Host "Version: $Version"
Write-Host "Output: $OutputPath"
Write-Host "Includes:"
foreach ($RelativePath in $BundleFiles) {
    Write-Host "  - $RelativePath"
}
Write-Host "Not an installer: this bundle packages release artifacts, docs, checksums, and rehearsal helpers for IT handoff."
Write-Host "Build release artifacts first with: bash scripts/verify-release.sh"

if ($PrintOnly) {
    exit 0
}

foreach ($RequiredPath in @($WheelPath, $SdistPath, $ChecksumsPath)) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Missing release artifact: $RequiredPath. Build artifacts first with: bash scripts/verify-release.sh"
    }
}

foreach ($RelativePath in $BundleFiles) {
    $AbsolutePath = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $AbsolutePath)) {
        throw "Missing bundle input: $RelativePath. Restore the file or update the bundle file list before retrying."
    }
}

if (Test-Path -LiteralPath $OutputPath) {
    throw "Output bundle already exists: $OutputPath. Choose a new -OutputPath or remove the existing file yourself before retrying."
}

$OutputDirectory = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $OutputDirectory)) {
    throw "Output directory does not exist: $OutputDirectory. Create it first or choose an existing -OutputPath directory."
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Zip = [System.IO.Compression.ZipFile]::Open($OutputPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($RelativePath in $BundleFiles) {
        $AbsolutePath = Join-Path $RepoRoot $RelativePath
        $ArchiveName = $RelativePath -replace "\\", "/"
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($Zip, $AbsolutePath, $ArchiveName) | Out-Null
    }
}
finally {
    $Zip.Dispose()
}

Write-Host "RELEASE-HANDOFF-BUNDLE: created $OutputPath"
