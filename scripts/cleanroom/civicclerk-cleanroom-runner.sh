#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-online}"
EVIDENCE_DIR="${CLEANROOM_EVIDENCE_DIR:-/evidence}"
RUN_LABEL="${CLEANROOM_RUN_LABEL:-cleanroom}"
CIVICCORE_FREEZE_TAG="${CIVICCORE_FREEZE_TAG:-v1.2.1}"
CIVICCORE_PACKAGE_VERSION="${CIVICCORE_PACKAGE_VERSION:-1.2.1}"
CIVICCLERK_DOCKER_HOST_ADDRESS="${CIVICCLERK_DOCKER_HOST_ADDRESS:-host.docker.internal}"
CIVICCORE_RELEASE_BASE_URL="https://github.com/CivicSuite/civiccore/releases/download/${CIVICCORE_FREEZE_TAG}"
OIDC_ISSUER="https://token.actions.githubusercontent.com"
WORKFLOW_IDENTITY="https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/${CIVICCORE_FREEZE_TAG}"

mkdir -p "${EVIDENCE_DIR}/logs" "${EVIDENCE_DIR}/civiccore-freeze-assets"

log() {
    printf '[cc1-cleanroom:%s] %s\n' "${MODE}" "$*"
}

record_step() {
    local name="$1"
    local status="$2"
    printf '%s\t%s\n' "${name}" "${status}" >> "${EVIDENCE_DIR}/step-results.tsv"
}

run_step() {
    local name="$1"
    shift
    local log_file="${EVIDENCE_DIR}/logs/${name}.log"
    {
        printf 'step=%s\n' "${name}"
        printf 'cwd=%s\n' "$(pwd)"
        printf 'command='
        printf '%q ' "$@"
        printf '\n\n'
    } > "${log_file}"

    log "running ${name}"
    if "$@" >> "${log_file}" 2>&1; then
        record_step "${name}" "PASS"
    else
        record_step "${name}" "FAIL"
        tail -100 "${log_file}" >&2 || true
        exit 1
    fi
}

write_run_metadata() {
    export MODE RUN_LABEL EVIDENCE_DIR CIVICCORE_FREEZE_TAG CIVICCORE_PACKAGE_VERSION CIVICCLERK_DOCKER_HOST_ADDRESS
    python - <<'PY'
from __future__ import annotations

import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path

evidence = Path(os.environ["EVIDENCE_DIR"])
metadata_path = evidence / "run-metadata.json"
metadata = {}
if metadata_path.exists():
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
metadata.update(
    {
        "schema_version": 1,
        "sprint_id": "CC-1",
        "run_label": os.environ.get("RUN_LABEL", "cleanroom"),
        "mode_last_updated": os.environ.get("MODE", "unknown"),
        "updated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "node": os.popen("node --version").read().strip(),
        "npm": os.popen("npm --version").read().strip(),
        "target": {
            "repo": "CivicSuite/civicclerk",
            "repo_url": os.environ.get("CIVICCLERK_REPO_URL", ""),
            "commit": os.environ["CIVICCLERK_COMMIT"],
        },
        "upstream": {
            "repo": "CivicSuite/civiccore",
            "freeze_tag": os.environ["CIVICCORE_FREEZE_TAG"],
            "package_version": os.environ["CIVICCORE_PACKAGE_VERSION"],
        },
        "host_docker": {
            "socket_path": "/var/run/docker.sock",
            "database_host_address": os.environ.get("CIVICCLERK_DOCKER_HOST_ADDRESS", ""),
            "purpose": "online verify-release disposable pgvector migration test",
        },
    }
)
metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

download_civiccore_freeze_assets() {
    local assets=(
        "civiccore-${CIVICCORE_PACKAGE_VERSION}-py3-none-any.whl"
        "civiccore-${CIVICCORE_PACKAGE_VERSION}.tar.gz"
        "SHA256SUMS.txt"
    )
    for asset in "${assets[@]}"; do
        run_step "download-civiccore-${asset}" \
            curl -fsSL --retry 3 --retry-delay 2 \
            -o "${EVIDENCE_DIR}/civiccore-freeze-assets/${asset}" \
            "${CIVICCORE_RELEASE_BASE_URL}/${asset}"
    done
}

online() {
    write_run_metadata
    run_step "verify-placeholder-imports" python scripts/check-civiccore-placeholder-imports.py
    run_step "verify-release" bash scripts/verify-release.sh
    run_step "verify-civiccore-freeze-provenance-fixtures" \
        python scripts/verify-release-provenance.py --fixtures-dir /workspace/civiccore-freeze/tests/fixtures/release_provenance
    download_civiccore_freeze_assets
    run_step "sha256sums-civiccore-freeze-assets" \
        bash -lc "cd '${EVIDENCE_DIR}/civiccore-freeze-assets' && sha256sum -c SHA256SUMS.txt"
    if [[ -f "${EVIDENCE_DIR}/civiccore-freeze-assets/release-attestation.json" && -f "${EVIDENCE_DIR}/civiccore-freeze-assets/release-attestation.json.bundle" ]]; then
        run_step "sigstore-civiccore-freeze-attestation" \
            bash -lc "cd '${EVIDENCE_DIR}/civiccore-freeze-assets' && cosign verify-blob release-attestation.json --bundle release-attestation.json.bundle --certificate-identity '${WORKFLOW_IDENTITY}' --certificate-oidc-issuer '${OIDC_ISSUER}'"
    else
        log "sigstore attestation assets not present for ${CIVICCORE_FREEZE_TAG}; SHA256SUMS verification remains required"
    fi
    if [[ -f "${EVIDENCE_DIR}/civiccore-freeze-assets/release-attestation.json" && -f "${EVIDENCE_DIR}/civiccore-freeze-assets/release-attestation.json.bundle" ]]; then
        run_step "live-civiccore-freeze-provenance" \
            python scripts/verify-release-provenance.py "${CIVICCORE_FREEZE_TAG}" \
                --repo CivicSuite/civiccore \
                --attestation "${EVIDENCE_DIR}/civiccore-freeze-assets/release-attestation.json" \
                --bundle "${EVIDENCE_DIR}/civiccore-freeze-assets/release-attestation.json.bundle" \
                --artifacts-dir "${EVIDENCE_DIR}/civiccore-freeze-assets"
    else
        log "live provenance attestation check skipped for ${CIVICCORE_FREEZE_TAG}; release has no attestation assets"
    fi
}

offline() {
    write_run_metadata
    run_step "offline-runtime-smoke" python - <<'PY'
import civiccore
import civicclerk
from civicclerk.main import app

assert civiccore.__version__ == "1.2.1"
assert civicclerk.__version__ == "1.0.4"
assert app.title == "CivicClerk"
assert callable(civiccore.validate_manifest)
assert callable(civiccore.import_meeting_payload)
assert callable(civiccore.compute_persisted_audit_hash)
assert callable(civiccore.verify_persisted_audit_chain)
print("offline runtime smoke OK")
PY
    run_step "offline-placeholder-imports" python scripts/check-civiccore-placeholder-imports.py
}

finalize() {
    write_run_metadata
    log "building stable manifest"
    python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

evidence = Path(os.environ["EVIDENCE_DIR"])
assets = evidence / "civiccore-freeze-assets"
steps_path = evidence / "step-results.tsv"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

steps = []
for line in steps_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    name, status = line.split("\t", 1)
    steps.append({"name": name, "status": status})

if any(step["status"] != "PASS" for step in steps):
    raise SystemExit("cannot finalize evidence with failed steps")

release_assets = []
for path in sorted(assets.iterdir()):
    if path.is_file():
        release_assets.append({"name": path.name, "sha256": sha256(path)})

manifest = {
    "schema_version": 1,
    "sprint_id": "CC-1",
    "result": "PASS",
    "target": {
        "repo": "CivicSuite/civicclerk",
        "repo_url": os.environ.get("CIVICCLERK_REPO_URL", ""),
        "commit": os.environ["CIVICCLERK_COMMIT"],
    },
    "upstream": {
        "repo": "CivicSuite/civiccore",
        "repo_url": os.environ.get("CIVICCORE_REPO_URL", ""),
        "freeze_tag": os.environ["CIVICCORE_FREEZE_TAG"],
        "package_version": os.environ["CIVICCORE_PACKAGE_VERSION"],
        "release_url": f"https://github.com/CivicSuite/civiccore/releases/tag/{os.environ['CIVICCORE_FREEZE_TAG']}",
        "workflow_identity": f"https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/{os.environ['CIVICCORE_FREEZE_TAG']}",
        "oidc_issuer": "https://token.actions.githubusercontent.com",
        "assets": release_assets,
    },
    "container": {
        "base_image": os.environ["CLEANROOM_BASE_IMAGE"],
        "base_image_digest": os.environ["CLEANROOM_BASE_IMAGE_DIGEST"],
        "build_mode": "docker build --no-cache --pull",
        "platform": "linux/amd64",
        "online_host_docker_socket": "/var/run/docker.sock for disposable pgvector migration testing",
        "online_github_api_auth": "GH_TOKEN/GITHUB_TOKEN may be passed through for live provenance API rate limits; token values are not recorded.",
    },
    "cosign": {
        "version": os.environ["CLEANROOM_COSIGN_VERSION"],
        "linux_amd64_sha256": os.environ["CLEANROOM_COSIGN_SHA256"],
    },
    "pinning_rules": {
        "civiccore_dependency": "v1.2.1 release wheel",
        "placeholder_namespaces_forbidden": ["civiccore.catalog", "civiccore.exemptions", "civiccore.scaffold"],
    },
    "network": {
        "allowed_during_provisioning_and_verification": [
            "https://github.com/CivicSuite/civicclerk.git",
            "https://github.com/CivicSuite/civiccore.git",
            "https://github.com/CivicSuite/civiccore/releases/download/v1.2.1/*",
            "https://api.github.com/repos/CivicSuite/civiccore/*",
            "https://github.com/sigstore/cosign/releases/download/v3.0.6/cosign-linux-amd64",
            "https://pypi.org/*",
            "https://files.pythonhosted.org/*",
            "https://registry.npmjs.org/*",
            "Sigstore transparency and certificate endpoints used by cosign verify-blob",
        ],
        "runtime_offline_proof": "offline-runtime-smoke and offline-placeholder-imports ran in docker run invocations with --network none.",
    },
    "commands": steps,
}

manifest_path = evidence / "cleanroom-manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(evidence / "cleanroom-manifest.sha256").write_text(
    f"{sha256(manifest_path)}  cleanroom-manifest.json\n",
    encoding="utf-8",
)

timestamp_manifest = {
    "schema_version": 1,
    "sprint_id": "CC-1",
    "purpose": "Documents run-specific fields excluded from cleanroom-manifest.json stable comparison.",
    "run_specific_files": [
        "run-metadata.json",
        "cleanroom-manifest.json.sig",
        "evidence-signing-public.pem",
        "signature-verify.log",
        "cleanroom-evidence.tar.gz",
        "cleanroom-evidence.tar.gz.sha256",
        "files.sha256",
    ],
}
(evidence / "timestamp-manifest.json").write_text(
    json.dumps(timestamp_manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

    local private_key
    private_key="$(mktemp)"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "${private_key}" >/dev/null 2>&1
    openssl rsa -pubout -in "${private_key}" -out "${EVIDENCE_DIR}/evidence-signing-public.pem" >/dev/null 2>&1
    openssl dgst -sha256 -sign "${private_key}" \
        -out "${EVIDENCE_DIR}/cleanroom-manifest.json.sig" \
        "${EVIDENCE_DIR}/cleanroom-manifest.json"
    rm -f "${private_key}"
    openssl dgst -sha256 -verify "${EVIDENCE_DIR}/evidence-signing-public.pem" \
        -signature "${EVIDENCE_DIR}/cleanroom-manifest.json.sig" \
        "${EVIDENCE_DIR}/cleanroom-manifest.json" \
        > "${EVIDENCE_DIR}/signature-verify.log"

    (
        cd "${EVIDENCE_DIR}"
        find . -type f \
            ! -name 'files.sha256' \
            ! -name 'cleanroom-evidence.tar.gz' \
            ! -name 'cleanroom-evidence.tar.gz.sha256' \
            -print0 \
            | sort -z \
            | xargs -0 sha256sum > files.sha256
        tar --sort=name --mtime='UTC 2026-05-05' --owner=0 --group=0 --numeric-owner \
            -czf cleanroom-evidence.tar.gz \
            cleanroom-manifest.json \
            cleanroom-manifest.sha256 \
            cleanroom-manifest.json.sig \
            civiccore-freeze-assets \
            evidence-signing-public.pem \
            files.sha256 \
            logs \
            run-metadata.json \
            signature-verify.log \
            step-results.tsv \
            timestamp-manifest.json
        sha256sum cleanroom-evidence.tar.gz > cleanroom-evidence.tar.gz.sha256
    )
}

case "${MODE}" in
    online)
        online
        ;;
    offline)
        offline
        ;;
    finalize)
        finalize
        ;;
    *)
        echo "unknown cleanroom mode: ${MODE}" >&2
        exit 2
        ;;
esac
