#!/usr/bin/env bash
set -euo pipefail

rehearsal_root=".backup-restore-rehearsal"
run_id="run-$(date -u +%Y%m%d-%H%M%S)"
strict=0
print_only=0

usage() {
  cat <<'EOF'
Usage: bash scripts/start_backup_restore_rehearsal.sh [--rehearsal-root PATH] [--run-id ID] [--strict] [--print-only]

Creates a local CivicClerk backup/restore rehearsal using SQLite stores and
packet export files, then verifies restored records can be reopened.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rehearsal-root)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --rehearsal-root." >&2
        exit 2
      fi
      rehearsal_root="$2"
      shift 2
      ;;
    --run-id)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --run-id." >&2
        exit 2
      fi
      run_id="$2"
      shift 2
      ;;
    --strict)
      strict=1
      shift
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

echo "CivicClerk backup/restore rehearsal profile"
echo "Rehearsal root: $rehearsal_root"
echo "Run id: $run_id"
echo "Python verifier: python scripts/check_backup_restore_rehearsal.py"
echo "Source stores: source-data/agenda-intake.db, source-data/agenda-items.db, source-data/meetings.db, source-data/packet-assembly.db, source-data/notice-checklist.db"
echo "Backup manifest: backup/civicclerk-backup-manifest.json"
echo "Restored stores: restored-data/*.db"
echo "Restored export root: restored-exports"
echo "Verification: database checksums, export checksums, restored agenda intake, agenda item, meeting, packet assembly, and notice checklist records"
echo "Fix path: if the run fails, inspect the named file under $rehearsal_root/$run_id, fix the backup source or env var, then rerun with a new --run-id."

args=(
  "scripts/check_backup_restore_rehearsal.py"
  "--rehearsal-root" "$rehearsal_root"
  "--run-id" "$run_id"
)
if [[ "$strict" -eq 1 ]]; then
  args+=("--strict")
fi
if [[ "$print_only" -eq 1 ]]; then
  args+=("--print-only")
fi

cd "$repo_root"
export PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}"
if command -v python3 >/dev/null 2>&1; then
  python_cmd=(python3)
elif command -v python >/dev/null 2>&1; then
  python_cmd=(python)
elif command -v py >/dev/null 2>&1; then
  python_cmd=(py -3)
else
  echo "Python is required for the backup/restore rehearsal. Install Python 3 or rerun from Windows PowerShell with scripts/start_backup_restore_rehearsal.ps1." >&2
  exit 1
fi

"${python_cmd[@]}" "${args[@]}"
