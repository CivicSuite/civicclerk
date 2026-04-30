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
