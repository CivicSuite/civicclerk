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

sign_requested="${CIVICCLERK_SIGN_INSTALLER:-false}"
normalized_sign_requested="$(printf '%s' "$sign_requested" | tr '[:upper:]' '[:lower:]')"
case "$normalized_sign_requested" in
  1|true|yes|on)
    SIGNTOOL_PATH="${CIVICCLERK_SIGNTOOL_PATH:-${SIGNTOOL:-signtool}}"
    if ! command -v "$SIGNTOOL_PATH" >/dev/null 2>&1 && [[ ! -x "$SIGNTOOL_PATH" ]]; then
      echo "Installer signing was requested, but SignTool was not found. Set CIVICCLERK_SIGNTOOL_PATH=/path/to/signtool.exe." >&2
      exit 1
    fi
    timestamp_url="${CIVICCLERK_SIGNING_TIMESTAMP_URL:-}"
    if [[ -z "$timestamp_url" ]]; then
      echo "Installer signing requires CIVICCLERK_SIGNING_TIMESTAMP_URL=<enterprise RFC 3161 timestamp URL>." >&2
      exit 1
    fi
    sign_args=(sign /fd sha256 /td sha256 /tr "$timestamp_url")
    if [[ -n "${CIVICCLERK_SIGNING_CERT_SHA1:-}" ]]; then
      sign_args+=(/sha1 "$CIVICCLERK_SIGNING_CERT_SHA1")
    elif [[ -n "${CIVICCLERK_SIGNING_PFX:-}" ]]; then
      sign_args+=(/f "$CIVICCLERK_SIGNING_PFX")
      password_env_name="${CIVICCLERK_SIGNING_PFX_PASSWORD_ENV:-}"
      if [[ -z "$password_env_name" || -z "${!password_env_name:-}" ]]; then
        echo "PFX signing requires CIVICCLERK_SIGNING_PFX_PASSWORD_ENV to name a populated password env var." >&2
        exit 1
      fi
      sign_args+=(/p "${!password_env_name}")
    else
      echo "Installer signing requires CIVICCLERK_SIGNING_CERT_SHA1 or CIVICCLERK_SIGNING_PFX." >&2
      exit 1
    fi
    "$SIGNTOOL_PATH" "${sign_args[@]}" "$artifact"
    echo "Signed $artifact"
    ;;
  *)
    echo "Installer signing skipped. Set CIVICCLERK_SIGN_INSTALLER=true after configuring SignTool, a certificate identity, and timestamp URL."
    ;;
esac

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$artifact"
fi
