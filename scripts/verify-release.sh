#!/usr/bin/env bash
# CivicClerk release gate.
set -euo pipefail

choose_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    if "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
      echo "$PYTHON"
      return 0
    fi
  fi
  for candidate in \
    python \
    /mnt/c/Users/scott/AppData/Local/Python/pythoncore-3.14-64/python.exe \
    python3
  do
    if command -v "$candidate" >/dev/null 2>&1 || [[ -x "$candidate" ]]; then
      if "$candidate" -c "import pytest" >/dev/null 2>&1; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  for candidate in python python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if ! PYTHON=$(choose_python); then
  echo "VERIFY-RELEASE: FAILED - python or python3 is required"
  exit 1
fi

echo "==> pytest"
"$PYTHON" -m pytest --ignore=tests/test_milestone_12_release.py

echo "==> docs"
bash scripts/verify-docs.sh

echo "==> recovery gates"
"$PYTHON" scripts/verify-recovery-gates.py

echo "==> secret scan"
"$PYTHON" scripts/verify-secret-scan.py

echo "==> placeholder imports"
"$PYTHON" scripts/check-civiccore-placeholder-imports.py

echo "==> browser QA"
"$PYTHON" scripts/verify-browser-qa.py

echo "==> prompt evals"
"$PYTHON" - <<'PY'
from __future__ import annotations

import os
import runpy

os.environ["CIVICCORE_LLM_PROVIDER"] = "ollama"
os.environ["CIVICCLERK_EVAL_OFFLINE"] = "1"
os.environ["NO_NETWORK"] = "1"
runpy.run_path("scripts/run-prompt-evals.py", run_name="__main__")
PY

if [[ -f "frontend/package-lock.json" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "VERIFY-RELEASE: FAILED - npm is required for frontend verification"
    exit 1
  fi
  echo "==> frontend dependencies"
  npm --prefix frontend ci

  echo "==> frontend audit"
  npm --prefix frontend audit --audit-level=moderate

  echo "==> frontend build"
  npm --prefix frontend run build

  echo "==> frontend tests"
  npm --prefix frontend test

  echo "==> frontend Playwright user flows"
  npx --prefix frontend playwright install chromium
  npm --prefix frontend run test:e2e
fi

echo "==> build dependencies"
"$PYTHON" -m pip install --quiet build

echo "==> clean dist"
rm -rf dist

echo "==> build"
export SOURCE_DATE_EPOCH=1777161600
"$PYTHON" -m build

echo "==> checksums"
"$PYTHON" - <<'PY'
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tomllib

dist = Path("dist")
version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
artifacts = [
    dist / f"civicclerk-{version}-py3-none-any.whl",
    dist / f"civicclerk-{version}.tar.gz",
]
missing = [str(path) for path in artifacts if not path.exists()]
if missing:
    raise SystemExit("Missing release artifacts: " + ", ".join(missing))

lines = []
for artifact in artifacts:
    lines.append(f"{sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}")
(dist / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("SHA256SUMS.txt")
PY

echo "==> runtime install proof"
version=$("$PYTHON" - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])
PY
)
proof_dir=$(mktemp -d)
trap 'rm -rf "$proof_dir"' EXIT
"$PYTHON" -m venv "$proof_dir/venv"
proof_python="$proof_dir/venv/bin/python"
if [[ ! -x "$proof_python" ]]; then
  proof_python="$proof_dir/venv/Scripts/python.exe"
fi
"$proof_python" -m pip install --quiet --upgrade pip
"$proof_python" -m pip install --quiet "dist/civicclerk-${version}-py3-none-any.whl"
"$proof_python" - <<'PY'
from fastapi.testclient import TestClient
from civicclerk.main import app

client = TestClient(app)
health = client.get("/health")
assert health.status_code == 200, health.text
payload = health.json()
assert payload["status"] == "ok", payload
assert payload["version"] == "1.0.0", payload
staff = client.get("/staff")
assert staff.status_code == 200, staff.text[:300]
print("RUNTIME-INSTALL-PROOF: PASSED")
PY

echo "==> release contract"
"$PYTHON" -m pytest tests/test_milestone_12_release.py

echo "VERIFY-RELEASE: PASSED"
