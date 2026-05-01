#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ISS="$ROOT/installer/windows/civicclerk.iss"
OUTPUT_DIR="$ROOT/installer/windows/build"

APP_VERSION="${CIVICCLERK_VERSION:-}"
if [[ -z "$APP_VERSION" ]]; then
  PYTHON_CMD=()
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=(python3)
  elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=(python)
  elif command -v py >/dev/null 2>&1; then
    PYTHON_CMD=(py -3)
  else
    echo "Python 3 was not found. Install Python 3 or set CIVICCLERK_VERSION=<semver> before building the installer." >&2
    exit 1
  fi
  APP_VERSION="$(
    "${PYTHON_CMD[@]}" - <<'PY'
from pathlib import Path
import tomllib
data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
print(data["project"]["version"])
PY
  )"
fi

required=(
  "install.ps1"
  "docker-compose.yml"
  "Dockerfile.backend"
  "Dockerfile.frontend"
  "docker/nginx.conf"
  "docs/examples/docker.env.example"
  "frontend/package.json"
  "civicclerk/main.py"
  "README.md"
  "USER-MANUAL.md"
  "CHANGELOG.md"
  "LICENSE"
)

for path in "${required[@]}"; do
  if [[ ! -e "$ROOT/$path" ]]; then
    echo "Missing required installer source: $path" >&2
    exit 1
  fi
done

ISCC="${ISCC:-}"
if [[ -z "$ISCC" ]]; then
  for candidate in \
    "/c/Program Files (x86)/Inno Setup 6/ISCC.exe" \
    "/c/Program Files/Inno Setup 6/ISCC.exe"; do
    if [[ -x "$candidate" ]]; then
      ISCC="$candidate"
      break
    fi
  done
fi

if [[ -z "$ISCC" || ! -x "$ISCC" ]]; then
  echo "Inno Setup compiler was not found. Install Inno Setup 6 or set ISCC=/path/to/ISCC.exe." >&2
  exit 1
fi

rm -rf "$OUTPUT_DIR"
"$ISCC" "$ISS" "/DMyAppVersion=$APP_VERSION"

artifact="$OUTPUT_DIR/CivicClerk-$APP_VERSION-Setup.exe"
if [[ ! -f "$artifact" ]]; then
  echo "Expected installer artifact was not produced: $artifact" >&2
  exit 1
fi

echo "Built $artifact"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$artifact"
fi
