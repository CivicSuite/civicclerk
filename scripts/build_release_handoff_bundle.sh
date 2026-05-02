#!/usr/bin/env bash
set -euo pipefail

version="0.1.14"
output_path=""
print_only=0

usage() {
  cat <<'EOF'
Usage: bash scripts/build_release_handoff_bundle.sh [--version VERSION] [--output-path PATH] [--print-only]

Builds a non-installer CivicClerk release handoff zip after release artifacts
have been generated with: bash scripts/verify-release.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --version." >&2
        exit 2
      fi
      version="$2"
      shift 2
      ;;
    --output-path)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --output-path." >&2
        exit 2
      fi
      output_path="$2"
      shift 2
      ;;
    --print-only)
      print_only=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
dist_root="$repo_root/dist"

if [[ -z "$output_path" ]]; then
  output_path="$dist_root/civicclerk-$version-release-handoff.zip"
fi

bundle_files=(
  "README.md"
  "README.txt"
  "USER-MANUAL.md"
  "USER-MANUAL.txt"
  "CHANGELOG.md"
  "LICENSE"
  "docs/index.html"
  "docs/examples/deployment.env.example"
  "docs/examples/trusted-header-nginx.conf"
  "scripts/check_installer_readiness.py"
  "scripts/check_pilot_readiness.py"
  "scripts/check_enterprise_installer_signing.py"
  "scripts/check_connector_sync_readiness.py"
  "scripts/run_mock_city_environment_suite.py"
  "scripts/check_vendor_live_sync_readiness.py"
  "scripts/run_connector_import_sync.py"
  "scripts/run_vendor_live_sync.py"
  "scripts/start_fresh_install_rehearsal.ps1"
  "scripts/start_fresh_install_rehearsal.sh"
  "scripts/check_backup_restore_rehearsal.py"
  "scripts/check_protected_deployment_smoke.py"
  "scripts/start_backup_restore_rehearsal.ps1"
  "scripts/start_backup_restore_rehearsal.sh"
  "scripts/start_protected_demo_rehearsal.ps1"
  "scripts/start_protected_demo_rehearsal.sh"
  "scripts/local_trusted_header_proxy.py"
  "dist/civicclerk-$version-py3-none-any.whl"
  "dist/civicclerk-$version.tar.gz"
  "dist/SHA256SUMS.txt"
)

echo "CivicClerk release handoff bundle"
echo "Version: $version"
echo "Output: $output_path"
echo "Includes:"
for relative_path in "${bundle_files[@]}"; do
  echo "  - $relative_path"
done
echo "Not an installer: this bundle packages release artifacts, docs, checksums, and rehearsal helpers for IT handoff."
echo "Build release artifacts first with: bash scripts/verify-release.sh"

if [[ "$print_only" -eq 1 ]]; then
  exit 0
fi

required_artifacts=(
  "$dist_root/civicclerk-$version-py3-none-any.whl"
  "$dist_root/civicclerk-$version.tar.gz"
  "$dist_root/SHA256SUMS.txt"
)

for required_path in "${required_artifacts[@]}"; do
  if [[ ! -f "$required_path" ]]; then
    echo "Missing release artifact: $required_path. Build artifacts first with: bash scripts/verify-release.sh" >&2
    exit 1
  fi
done

for relative_path in "${bundle_files[@]}"; do
  if [[ ! -f "$repo_root/$relative_path" ]]; then
    echo "Missing bundle input: $relative_path. Restore the file or update the bundle file list before retrying." >&2
    exit 1
  fi
done

if [[ -e "$output_path" ]]; then
  echo "Output bundle already exists: $output_path. Choose a new --output-path or remove the existing file yourself before retrying." >&2
  exit 1
fi

output_dir="$(dirname -- "$output_path")"
if [[ ! -d "$output_dir" ]]; then
  echo "Output directory does not exist: $output_dir. Create it first or choose an existing --output-path directory." >&2
  exit 1
fi

python_bin=""
if command -v python3 >/dev/null 2>&1; then
  python_bin="python3"
elif command -v python >/dev/null 2>&1; then
  python_bin="python"
else
  echo "Python is required to create the zip bundle. Install Python 3 or rerun with --print-only to preview the plan." >&2
  exit 1
fi

"$python_bin" - "$repo_root" "$output_path" "${bundle_files[@]}" <<'PY'
from pathlib import Path
import sys
import zipfile

repo_root = Path(sys.argv[1])
output_path = Path(sys.argv[2])
bundle_files = sys.argv[3:]

with zipfile.ZipFile(output_path, mode="x", compression=zipfile.ZIP_DEFLATED) as bundle:
    for relative_path in bundle_files:
        bundle.write(repo_root / relative_path, relative_path)
PY

echo "RELEASE-HANDOFF-BUNDLE: created $output_path"
