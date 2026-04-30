"""Milestone 12+ v0.1.11 release contract."""

from __future__ import annotations

import tomllib
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from civicclerk import __version__
from civicclerk.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_version_surfaces_are_synchronized_to_v0111() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    current_docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.txt").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        ]
    )
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert pyproject["project"]["version"] == "0.1.11"
    assert __version__ == "0.1.11"
    assert "Current version: `0.1.11`" in current_docs
    assert "Version: `0.1.11`" in current_docs
    assert "v0.1.11" in current_docs
    assert "0.1.0.dev0" not in current_docs
    assert "## [0.1.11] - 2026-04-30" in changelog


async def test_health_endpoint_reports_release_version() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["version"] == "0.1.11"


def test_verify_release_script_exists_and_mentions_all_release_gates() -> None:
    script = ROOT / "scripts" / "verify-release.sh"
    text = script.read_text(encoding="utf-8")

    assert script.exists()
    for gate in [
        "-m pytest",
        "bash scripts/verify-docs.sh",
        "scripts/check-civiccore-placeholder-imports.py",
        "scripts/verify-browser-qa.py",
        "scripts/run-prompt-evals.py",
        "-m build",
        "SHA256SUMS.txt",
    ]:
        assert gate in text

def test_release_workflow_and_docs_reference_v0111_release() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.txt").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    ).lower()

    assert "v*" in workflow
    assert "bash scripts/verify-release.sh" in workflow
    assert "contents: write" in workflow
    assert "gh release create" in workflow
    assert "dist/*" in workflow
    assert "civiccore/releases/download/v0.16.0/civiccore-0.16.0-py3-none-any.whl" in workflow
    assert "civicclerk v0.1.11" in docs
    assert "published `civiccore` v0.16.0 release wheel" in docs


def test_docs_include_fresh_machine_install_and_smoke_check_contract() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.txt").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    )

    for expected in [
        "python -m venv .venv",
        ".\\.venv\\Scripts\\Activate.ps1",
        "python -m pip install dist/civicclerk-0.1.11-py3-none-any.whl",
        "python -m uvicorn civicclerk.main:app --host 127.0.0.1 --port 8776",
        "http://127.0.0.1:8776/health",
        "/staff/auth-readiness",
        '$env:CIVICCLERK_STAFF_AUTH_MODE="open"',
        "scripts/start_protected_demo_rehearsal.ps1",
        "-PrintOnly",
        "127.0.0.1:8877",
        "127.0.0.1:8878",
    ]:
        assert expected in docs


def test_protected_demo_rehearsal_script_prints_expected_plan() -> None:
    import subprocess
    import shutil

    import pytest

    script = ROOT / "scripts" / "start_protected_demo_rehearsal.ps1"
    assert script.exists()
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell runtime is not available in this environment.")

    result = subprocess.run(
        [
            shell,
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-PrintOnly",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout
    for expected in [
        "Protected demo rehearsal profile",
        "CIVICCLERK_STAFF_AUTH_MODE=trusted_header",
        "CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES=127.0.0.1/32",
        "CIVICCLERK_LOCAL_PROXY_UPSTREAM=http://127.0.0.1:8877",
        "App command: python -m uvicorn civicclerk.main:app --host 127.0.0.1 --port 8877",
        "Proxy command: python scripts/local_trusted_header_proxy.py",
        "Smoke check: GET http://127.0.0.1:8877/health",
        "Readiness check: GET http://127.0.0.1:8877/staff/auth-readiness",
        "Browser check: open http://127.0.0.1:8878/staff",
    ]:
        assert expected in output
