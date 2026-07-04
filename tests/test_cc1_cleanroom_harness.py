from __future__ import annotations

import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE_WHEEL_URL = (
    "https://github.com/CivicSuite/civiccore/releases/download/"
    "v1.2.1/civiccore-1.2.1-py3-none-any.whl"
)
FREEZE_WHEEL_DEPENDENCY = (
    f"civiccore @ {FREEZE_WHEEL_URL}"
    "#sha256=8dde29408e206048bde63ec14156a8e6329382af4d16b12710d12aa5c27f3f59"
)


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_civiccore_dependency_is_pinned_to_freeze_release_asset() -> None:
    pyproject = tomllib.loads(read("pyproject.toml"))
    dependencies = pyproject["project"]["dependencies"]

    assert FREEZE_WHEEL_DEPENDENCY in dependencies
    assert not any("civiccore.git@main" in dep for dep in dependencies)

    for path in (
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/workflows/release-preflight.yml",
    ):
        text = read(path)
        assert FREEZE_WHEEL_URL in text
        assert "civiccore.git@main" not in text


def test_placeholder_import_checker_matches_co7_placeholder_namespaces() -> None:
    checker = read("scripts/check-civiccore-placeholder-imports.py")

    for placeholder in ("catalog", "exemptions", "scaffold"):
        assert f'"{placeholder}"' in checker

    for shipped_namespace in ("onboarding", "ingest", "search", "auth", "scheduling"):
        assert f'"{shipped_namespace}"' not in checker


def test_cleanroom_dockerfile_pins_base_image_cosign_and_target_commit() -> None:
    dockerfile = read("cleanroom/civicclerk.Dockerfile")

    assert "node:24-bookworm-slim@sha256:03eae3ef7e88a9de535496fb488d67e02b9d96a063a8967bae657744ecd513f2" in dockerfile
    assert "ARG COSIGN_VERSION=v3.0.6" in dockerfile
    assert "ARG COSIGN_SHA256=c956e5dfcac53d52bcf058360d579472f0c1d2d9b69f55209e256fe7783f4c74" in dockerfile
    assert "ARG CIVICCORE_FREEZE_REF=v1.2.1" in dockerfile
    assert "download.docker.com/linux/debian" in dockerfile
    assert "docker-ce-cli" in dockerfile
    assert "git fetch --depth 1 origin \"${CIVICCLERK_COMMIT}\"" in dockerfile
    assert 'test "$(git rev-parse HEAD)" = "${CIVICCLERK_COMMIT}"' in dockerfile
    assert "install -m 0755 scripts/cleanroom/civicclerk-cleanroom-runner.sh" in dockerfile
    assert "COPY scripts/cleanroom" not in dockerfile


def test_cleanroom_runner_verifies_freeze_tag_and_full_civicclerk_gate() -> None:
    runner = read("scripts/cleanroom/civicclerk-cleanroom-runner.sh")

    assert "bash scripts/verify-release.sh" in runner
    assert "python scripts/check-civiccore-placeholder-imports.py" in runner
    assert "v1.2.1" in runner
    assert "sha256sum -c SHA256SUMS.txt" in runner
    assert "cosign verify-blob release-attestation.json" in runner
    assert 'python scripts/verify-release-provenance.py "${CIVICCORE_FREEZE_TAG}"' in runner
    assert "offline-runtime-smoke" in runner
    assert "cleanroom-manifest.json.sig" in runner
    assert "timestamp-manifest.json" in runner


def test_cleanroom_orchestrator_uses_no_cache_two_runs_and_offline_phase() -> None:
    orchestrator = read("scripts/run-civicclerk-cleanroom.sh")

    assert "docker build --no-cache --pull --platform linux/amd64" in orchestrator
    assert 'RUN_COUNT="${CLEANROOM_RUN_COUNT:-2}"' in orchestrator
    assert "pick_python" in orchestrator
    assert '"${candidate[@]}" -c "import json, pathlib"' in orchestrator
    assert "--network none" in orchestrator
    assert "CLEANROOM_DOCKER_SOCKET" in orchestrator
    assert "CLEANROOM_DOCKER_GATEWAY_HOSTNAME" in orchestrator
    assert "host.docker.internal" in orchestrator
    assert "CIVICCLERK_DOCKER_HOST_ADDRESS" in orchestrator
    assert "GITHUB_AUTH_ENV" in orchestrator
    assert "GH_TOKEN" in orchestrator
    assert "cleanroom stable manifests differ" in orchestrator
    assert "identical_stable_manifests" in orchestrator


def test_cleanroom_ci_uploads_evidence_artifact() -> None:
    workflow = read(".github/workflows/cleanroom.yml")

    assert "CC1_SHA" in workflow
    assert "github.event.pull_request.head.sha" in workflow
    assert "fetch-depth: 0" in workflow
    assert "bash scripts/run-civicclerk-cleanroom.sh" in workflow
    assert "actions/upload-artifact" in workflow
    assert 'CLEANROOM_RUN_COUNT: "2"' in workflow
    assert "GITHUB_TOKEN: ${{ github.token }}" in workflow
    assert "v1.2.1" in workflow


def test_cleanroom_docs_define_evidence_and_upstream_trust_anchor() -> None:
    docs = "\n".join(
        [
            read("docs/ops/cc-1-cleanroom-harness.md"),
            read("docs/evidence/cc1-civicclerk-cleanroom/README.md"),
        ]
    )

    for expected in (
        "v1.2.1",
        "sha256sum -c SHA256SUMS.txt",
        "release-attestation.json",
        "cleanroom-manifest.json",
        "timestamp-manifest.json",
        "GitHub Actions artifact",
    ):
        assert expected in docs
