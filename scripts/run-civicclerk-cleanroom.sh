#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

TARGET_COMMIT="${1:-$(git rev-parse HEAD)}"
TARGET_COMMIT="$(git rev-parse "${TARGET_COMMIT}^{commit}")"
SHORT_SHA="${TARGET_COMMIT:0:12}"
EVIDENCE_ROOT="${2:-docs/evidence/cc1-civicclerk-cleanroom-${SHORT_SHA}}"
RUN_COUNT="${CLEANROOM_RUN_COUNT:-2}"
IMAGE_TAG="civicclerk-cleanroom:${SHORT_SHA}"
REPO_URL="${CIVICCLERK_REPO_URL:-https://github.com/CivicSuite/civicclerk.git}"
CORE_REPO_URL="${CIVICCORE_REPO_URL:-https://github.com/CivicSuite/civiccore.git}"
CORE_FREEZE_REF="${CIVICCORE_FREEZE_REF:-v1.0}"
DOCKER_SOCKET_PATH="${CLEANROOM_DOCKER_SOCKET:-/var/run/docker.sock}"
DOCKER_GATEWAY_HOSTNAME="${CLEANROOM_DOCKER_GATEWAY_HOSTNAME:-host.docker.internal}"
DOCKER_HOST_ADDRESS="${CIVICCLERK_DOCKER_HOST_ADDRESS:-${DOCKER_GATEWAY_HOSTNAME}}"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required to run the CivicClerk cleanroom harness." >&2
    exit 1
fi

if [ ! -S "${DOCKER_SOCKET_PATH}" ]; then
    echo "CivicClerk cleanroom requires a Docker socket at ${DOCKER_SOCKET_PATH}." >&2
    echo "Set CLEANROOM_DOCKER_SOCKET to the host Docker socket so verify-release can run the disposable pgvector migration test." >&2
    exit 1
fi

PYTHON_CMD=()
pick_python() {
    local -a candidate=("$@")
    if command -v "${candidate[0]}" >/dev/null 2>&1 && "${candidate[@]}" -c "import json, pathlib" >/dev/null 2>&1; then
        PYTHON_CMD=("${candidate[@]}")
        return 0
    fi
    return 1
}

if pick_python python; then
    :
elif pick_python python3; then
    :
elif pick_python python.exe; then
    :
elif pick_python py -3; then
    :
else
    echo "No usable Python interpreter found on PATH (checked python, python3, python.exe, py -3)." >&2
    exit 1
fi

if [ "${RUN_COUNT}" -lt 1 ]; then
    echo "CLEANROOM_RUN_COUNT must be at least 1." >&2
    exit 1
fi

if [ -n "${GITHUB_TOKEN:-}" ] && [ -z "${GH_TOKEN:-}" ]; then
    export GH_TOKEN="${GITHUB_TOKEN}"
elif [ -n "${GH_TOKEN:-}" ] && [ -z "${GITHUB_TOKEN:-}" ]; then
    export GITHUB_TOKEN="${GH_TOKEN}"
fi

GITHUB_AUTH_ENV=()
if [ -n "${GH_TOKEN:-}" ]; then
    GITHUB_AUTH_ENV=(-e GITHUB_TOKEN -e GH_TOKEN)
fi

host_path() {
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$1"
    else
        printf '%s' "$1"
    fi
}

run_dir_abs() {
    local path="$1"
    mkdir -p "${path}"
    (cd "${path}" && pwd)
}

echo "CC-1 cleanroom target commit: ${TARGET_COMMIT}"
echo "Evidence root: ${EVIDENCE_ROOT}"
echo "Run count: ${RUN_COUNT}"
echo "CivicCore freeze ref: ${CORE_FREEZE_REF}"
echo "Docker socket: ${DOCKER_SOCKET_PATH}"

DOCKER_BUILDKIT=1 docker build --no-cache --pull --platform linux/amd64 \
    --build-arg "CIVICCLERK_REPO_URL=${REPO_URL}" \
    --build-arg "CIVICCLERK_COMMIT=${TARGET_COMMIT}" \
    --build-arg "CIVICCORE_REPO_URL=${CORE_REPO_URL}" \
    --build-arg "CIVICCORE_FREEZE_REF=${CORE_FREEZE_REF}" \
    -f cleanroom/civicclerk.Dockerfile \
    -t "${IMAGE_TAG}" \
    .

rm -rf "${EVIDENCE_ROOT}"
mkdir -p "${EVIDENCE_ROOT}"

for idx in $(seq 1 "${RUN_COUNT}"); do
    label="run-${idx}"
    evidence_dir="${EVIDENCE_ROOT}/${label}"
    mkdir -p "${evidence_dir}"
    evidence_abs="$(run_dir_abs "${evidence_dir}")"
    evidence_mount="$(host_path "${evidence_abs}")"

    echo "Running online cleanroom phase: ${label}"
    MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --network bridge \
        --add-host "${DOCKER_GATEWAY_HOSTNAME}:host-gateway" \
        -e "CLEANROOM_RUN_LABEL=${label}" \
        -e "CIVICCLERK_COMMIT=${TARGET_COMMIT}" \
        -e "CIVICCORE_FREEZE_TAG=${CORE_FREEZE_REF}" \
        -e "CIVICCLERK_DOCKER_HOST_ADDRESS=${DOCKER_HOST_ADDRESS}" \
        -v "${DOCKER_SOCKET_PATH}:/var/run/docker.sock" \
        "${GITHUB_AUTH_ENV[@]}" \
        -v "${evidence_mount}:/evidence" \
        "${IMAGE_TAG}" online

    echo "Running offline cleanroom phase: ${label}"
    MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --network none \
        -e "CLEANROOM_RUN_LABEL=${label}" \
        -e "CIVICCLERK_COMMIT=${TARGET_COMMIT}" \
        -e "CIVICCORE_FREEZE_TAG=${CORE_FREEZE_REF}" \
        -v "${evidence_mount}:/evidence" \
        "${IMAGE_TAG}" offline

    echo "Finalizing cleanroom evidence: ${label}"
    MSYS_NO_PATHCONV=1 docker run --rm --platform linux/amd64 --network none \
        -e "CLEANROOM_RUN_LABEL=${label}" \
        -e "CIVICCLERK_COMMIT=${TARGET_COMMIT}" \
        -e "CIVICCORE_FREEZE_TAG=${CORE_FREEZE_REF}" \
        -v "${evidence_mount}:/evidence" \
        "${IMAGE_TAG}" finalize
done

"${PYTHON_CMD[@]}" - "${EVIDENCE_ROOT}" "${TARGET_COMMIT}" "${RUN_COUNT}" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
target_commit = sys.argv[2]
run_count = int(sys.argv[3])

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

manifests = []
for idx in range(1, run_count + 1):
    manifest_path = root / f"run-{idx}" / "cleanroom-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"missing manifest: {manifest_path}")
    manifests.append(
        {
            "run": f"run-{idx}",
            "path": str(manifest_path).replace("\\", "/"),
            "sha256": sha256(manifest_path),
            "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
        }
    )

manifest_hashes = [item["sha256"] for item in manifests]
identical = len(set(manifest_hashes)) == 1
comparison = {
    "schema_version": 1,
    "sprint_id": "CC-1",
    "target_commit": target_commit,
    "run_count": run_count,
    "identical_stable_manifests": identical,
    "manifest_hashes": [
        {"run": item["run"], "path": item["path"], "sha256": item["sha256"]}
        for item in manifests
    ],
    "timestamp_and_signature_note": (
        "run-metadata.json, timestamp-manifest.json, signatures, and compressed bundles are run-specific; "
        "cleanroom-manifest.json is the stable cross-machine comparison surface."
    ),
}
(root / "comparison.json").write_text(
    json.dumps(comparison, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

summary = [
    "# CC-1 CivicClerk Cleanroom Harness Evidence",
    "",
    f"Target commit: `{target_commit}`",
    f"Run count: {run_count}",
    f"Stable manifests identical: {str(identical).lower()}",
    "",
    "## Stable Manifest Hashes",
    "",
]
for item in comparison["manifest_hashes"]:
    summary.append(f"- `{item['run']}`: `{item['sha256']}`")
summary.extend(
    [
        "",
        "## Evidence",
        "",
        "- Each run directory contains `cleanroom-manifest.json`, logs, downloaded CivicCore freeze assets, a signed manifest, `timestamp-manifest.json`, and `cleanroom-evidence.tar.gz`.",
        "- `run-metadata.json`, signatures, timestamp manifests, and compressed bundle hashes are intentionally run-specific.",
        "- `comparison.json` is the machine-comparable summary.",
        "",
    ]
)
(root / "summary.md").write_text("\n".join(summary), encoding="utf-8")

if not identical:
    raise SystemExit("cleanroom stable manifests differ")
print(f"CC-1 cleanroom manifests match: {manifest_hashes[0]}")
PY
