#!/usr/bin/env bash
set -euo pipefail

app_port=8877
proxy_port=8878
principal="clerk@example.gov"
roles="clerk_admin,meeting_editor"
print_only=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-port)
      app_port="$2"
      shift 2
      ;;
    --proxy-port)
      proxy_port="$2"
      shift 2
      ;;
    --principal)
      principal="$2"
      shift 2
      ;;
    --roles)
      roles="$2"
      shift 2
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
repo_root="$(cd "$script_dir/.." && pwd)"
upstream_url="http://127.0.0.1:${app_port}"
proxy_url="http://127.0.0.1:${proxy_port}"
app_command="python -m uvicorn civicclerk.main:app --host 127.0.0.1 --port ${app_port}"
proxy_command="python scripts/local_trusted_header_proxy.py"

write_plan() {
  echo "Protected demo rehearsal profile"
  echo "Repo root: ${repo_root}"
  echo "App URL: ${upstream_url}"
  echo "Proxy URL: ${proxy_url}"
  echo "Export CIVICCLERK_STAFF_AUTH_MODE=trusted_header"
  echo "Export CIVICCLERK_STAFF_SSO_PROVIDER=local trusted-header rehearsal proxy"
  echo "Export CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER=X-Staff-Email"
  echo "Export CIVICCLERK_STAFF_SSO_ROLES_HEADER=X-Staff-Roles"
  echo "Export CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES=127.0.0.1/32"
  echo "Export CIVICCLERK_LOCAL_PROXY_UPSTREAM=${upstream_url}"
  echo "Export CIVICCLERK_LOCAL_PROXY_LISTEN_HOST=127.0.0.1"
  echo "Export CIVICCLERK_LOCAL_PROXY_LISTEN_PORT=${proxy_port}"
  echo "Export CIVICCLERK_LOCAL_PROXY_PRINCIPAL=${principal}"
  echo "Export CIVICCLERK_LOCAL_PROXY_ROLES=${roles}"
  echo "App command: ${app_command}"
  echo "Proxy command: ${proxy_command}"
  echo "Smoke check: GET ${upstream_url}/health"
  echo "Readiness check: GET ${upstream_url}/staff/auth-readiness"
  echo "Browser check: open ${proxy_url}/staff"
  echo "Stop both Python processes when the rehearsal ends."
}

export CIVICCLERK_STAFF_AUTH_MODE="trusted_header"
export CIVICCLERK_STAFF_SSO_PROVIDER="local trusted-header rehearsal proxy"
export CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER="X-Staff-Email"
export CIVICCLERK_STAFF_SSO_ROLES_HEADER="X-Staff-Roles"
export CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES="127.0.0.1/32"
export CIVICCLERK_LOCAL_PROXY_UPSTREAM="${upstream_url}"
export CIVICCLERK_LOCAL_PROXY_LISTEN_HOST="127.0.0.1"
export CIVICCLERK_LOCAL_PROXY_LISTEN_PORT="${proxy_port}"
export CIVICCLERK_LOCAL_PROXY_PRINCIPAL="${principal}"
export CIVICCLERK_LOCAL_PROXY_ROLES="${roles}"

write_plan

if [[ "${print_only}" -eq 1 ]]; then
  exit 0
fi

cd "${repo_root}"
python -m uvicorn civicclerk.main:app --host 127.0.0.1 --port "${app_port}" &
app_pid=$!

sleep 3

python scripts/local_trusted_header_proxy.py &
proxy_pid=$!

echo "Started app PID: ${app_pid}"
echo "Started proxy PID: ${proxy_pid}"
echo "Browse ${proxy_url}/staff to exercise the protected demo profile."
