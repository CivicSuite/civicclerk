#!/usr/bin/env bash
set -euo pipefail

wheel_path="dist/civicclerk-0.1.17-py3-none-any.whl"
rehearsal_root=".fresh-install-rehearsal"
app_port=8776
keep_server=0
print_only=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wheel-path)
      wheel_path="$2"
      shift 2
      ;;
    --rehearsal-root)
      rehearsal_root="$2"
      shift 2
      ;;
    --app-port)
      app_port="$2"
      shift 2
      ;;
    --keep-server)
      keep_server=1
      shift
      ;;
    --print-only)
      print_only=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
host_python="$(command -v python3 || command -v python || true)"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    venv_python_relative="Scripts/python.exe"
    ;;
  *)
    venv_python_relative="bin/python"
    ;;
esac

resolve_path() {
  local path_value="$1"
  case "${path_value}" in
    /*|[A-Za-z]:/*|[A-Za-z]:\\*)
      printf '%s\n' "${path_value}"
      ;;
    *)
      printf '%s\n' "${repo_root}/${path_value}"
      ;;
  esac
}

resolved_wheel_path="$(resolve_path "${wheel_path}")"
resolved_rehearsal_root="$(resolve_path "${rehearsal_root}")"
venv_path="${resolved_rehearsal_root}/.venv"
python_path="${venv_path}/${venv_python_relative}"
app_url="http://127.0.0.1:${app_port}"

write_plan() {
  echo "Fresh install rehearsal profile"
  echo "Repo root: ${repo_root}"
  echo "Wheel path: ${resolved_wheel_path}"
  echo "Rehearsal root: ${resolved_rehearsal_root}"
  echo "Virtual environment: ${venv_path}"
  echo "Host Python: ${host_python:-not found}"
  echo "Create venv: ${host_python:-python3} -m venv ${venv_path}"
  echo "Upgrade pip: ${python_path} -m pip install --upgrade pip"
  echo "Install wheel: ${python_path} -m pip install ${resolved_wheel_path}"
  echo "Export CIVICCLERK_STAFF_AUTH_MODE=open"
  echo "App command: ${python_path} -m uvicorn civicclerk.main:app --host 127.0.0.1 --port ${app_port}"
  echo "Smoke check: GET ${app_url}/health"
  echo "Readiness check: GET ${app_url}/staff/auth-readiness"
  echo "Browser check: open ${app_url}/staff"
  echo 'Expected health: {"status":"ok","service":"civicclerk","version":"0.1.17","civiccore":"0.19.0"}'
  echo "If the wheel is missing, build it first with: python -m build"
  echo "If port ${app_port} is already in use, stop the existing process or rerun with --app-port set to an available port."
  echo "By default this helper stops the app after smoke checks; pass --keep-server to keep it running."
}

port_available() {
  "${host_python}" - "${app_port}" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        raise SystemExit(1)
PY
}

json_get() {
  "${python_path}" - "$1" <<'PY'
import json
import sys
from urllib.request import urlopen

with urlopen(sys.argv[1], timeout=10) as response:
    print(json.dumps(json.load(response), sort_keys=True))
PY
}

write_plan

if [[ "${print_only}" -eq 1 ]]; then
  exit 0
fi

if [[ -z "${host_python}" ]]; then
  echo "Fresh install rehearsal needs Python on PATH. Install Python 3 or add python3/python to PATH, then rerun this helper." >&2
  exit 1
fi

if [[ ! -f "${resolved_wheel_path}" ]]; then
  echo "Fresh install rehearsal cannot find the wheel at '${resolved_wheel_path}'. Build the release artifact first with 'python -m build', then rerun this helper." >&2
  exit 1
fi

if ! port_available; then
  echo "Fresh install rehearsal cannot use 127.0.0.1:${app_port} because the port is already in use. Stop the existing local process or rerun this helper with --app-port set to an available port." >&2
  exit 1
fi

mkdir -p "${resolved_rehearsal_root}"
if ! venv_output="$("${host_python}" -m venv "${venv_path}" 2>&1)"; then
  echo "${venv_output}" >&2
  echo "Fresh install rehearsal could not create the virtual environment. Install Python's venv support for this shell, such as python3-venv on Debian/Ubuntu, or use Git Bash with a Python distribution that includes venv." >&2
  exit 1
fi
"${python_path}" -m pip install --upgrade pip
"${python_path}" -m pip install "${resolved_wheel_path}"

export CIVICCLERK_STAFF_AUTH_MODE="open"
cd "${resolved_rehearsal_root}"
"${python_path}" -m uvicorn civicclerk.main:app --host 127.0.0.1 --port "${app_port}" &
app_pid=$!

cleanup() {
  if [[ "${keep_server}" -ne 1 ]] && kill -0 "${app_pid}" 2>/dev/null; then
    kill "${app_pid}"
    wait "${app_pid}" 2>/dev/null || true
    echo "Stopped fresh install rehearsal app PID: ${app_pid}"
  fi
}
trap cleanup EXIT

health=""
for _ in {1..20}; do
  if health="$(json_get "${app_url}/health" 2>/dev/null)"; then
    break
  fi
  sleep 1
done

expected='{"civiccore": "0.19.0", "service": "civicclerk", "status": "ok", "version": "0.1.17"}'
if [[ -z "${health}" ]]; then
  echo "The installed CivicClerk app did not answer ${app_url}/health within 20 seconds. Check the app process output and whether port ${app_port} is already in use." >&2
  exit 1
fi
if [[ "${health}" != "${expected}" ]]; then
  echo "Unexpected /health response: ${health}. Expected CivicClerk 0.1.17 with CivicCore 0.19.0." >&2
  exit 1
fi

readiness="$(json_get "${app_url}/staff/auth-readiness")"
if [[ "${readiness}" != *'"mode": "open"'* ]]; then
  echo "Unexpected /staff/auth-readiness response: ${readiness}. Expected mode 'open' for the fresh install rehearsal." >&2
  exit 1
fi

"${python_path}" - "${app_url}/staff" <<'PY'
import sys
from urllib.request import urlopen

with urlopen(sys.argv[1], timeout=10) as response:
    body = response.read().decode("utf-8")
    if response.status != 200 or "CivicClerk" not in body:
        raise SystemExit("Unexpected /staff response. Expected HTTP 200 with the CivicClerk staff workflow shell.")
PY

echo "Fresh install smoke checks passed."
echo "Verified ${app_url}/health"
echo "Verified ${app_url}/staff/auth-readiness"
echo "Verified ${app_url}/staff"

if [[ "${keep_server}" -eq 1 ]]; then
  trap - EXIT
  echo "Keeping app running at ${app_url} with PID ${app_pid}. Stop it manually when the rehearsal ends."
fi
