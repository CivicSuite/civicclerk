from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


ROOT = Path(__file__).resolve().parents[1]


def load_pyproject() -> dict:
    pyproject = ROOT / "pyproject.toml"
    assert pyproject.exists(), "pyproject.toml must exist for the CivicClerk runtime foundation."
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))


def load_app_module():
    try:
        spec = importlib.util.find_spec("civicclerk.main")
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, "civicclerk.main must be importable."
    return importlib.import_module("civicclerk.main")


def test_pyproject_declares_runtime_package_and_version() -> None:
    data = load_pyproject()

    assert data["project"]["name"] == "civicclerk"
    assert data["project"]["version"] == "0.1.12"
    assert "CivicClerk" in data["project"]["description"]


def test_pyproject_targets_published_civiccore_v0150_release_wheel() -> None:
    data = load_pyproject()
    dependencies = data["project"]["dependencies"]

    assert (
        "civiccore @ https://github.com/CivicSuite/civiccore/releases/download/v0.16.0/"
        "civiccore-0.16.0-py3-none-any.whl"
    ) in dependencies
    assert not any(
        "civiccore>=" in dep or "civiccore~=" in dep or dep == "civiccore==0.12.0"
        for dep in dependencies
    )


def test_pyproject_declares_foundation_runtime_and_test_dependencies() -> None:
    data = load_pyproject()
    dependencies = "\n".join(data["project"]["dependencies"])
    dev_dependencies = "\n".join(data["project"]["optional-dependencies"]["dev"])

    assert "fastapi" in dependencies
    assert "uvicorn" in dependencies
    assert "pytest" in dev_dependencies
    assert "httpx" in dev_dependencies


def test_runtime_package_layout_exists() -> None:
    expected_paths = [
        ROOT / "civicclerk" / "__init__.py",
        ROOT / "civicclerk" / "main.py",
    ]

    for path in expected_paths:
        assert path.exists(), f"Missing runtime foundation file: {path.relative_to(ROOT)}"


def test_public_fastapi_app_import_path_exists() -> None:
    module = load_app_module()
    assert isinstance(module.app, FastAPI)
    assert module.app.title == "CivicClerk"


@pytest.mark.asyncio
async def test_root_endpoint_explains_current_user_experience() -> None:
    module = load_app_module()
    async with AsyncClient(
        transport=ASGITransport(app=module.app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "CivicClerk"
    assert payload["status"] == "v0.1.12 runtime foundation release"
    assert "full integrated clerk console remains future work" in payload["message"]
    assert "notice compliance" in payload["message"]
    assert "motion" in payload["message"]
    assert "vote" in payload["message"]
    assert "minutes" in payload["message"]
    assert "archive" in payload["message"]
    assert "prompt YAML" in payload["message"]
    assert "Granicus" in payload["message"]
    assert "keyboard" in payload["message"]
    assert "shared CivicCore notice compliance helper" in payload["message"]
    assert "v0.1.12" in payload["message"]
    assert "trusted-header reverse-proxy mode" in payload["message"]
    assert "trusted-proxy CIDR allowlist" in payload["message"]
    assert "agenda intake queue" in payload["message"]
    assert "packet assembly records" in payload["message"]
    assert "notice checklist records" in payload["message"]
    assert "staff workflow screens" in payload["message"]
    assert "staff agenda intake screen can now submit items" in payload["message"]
    assert "persist posting proof through live API actions" in payload["message"]
    assert "meeting records can now persist" in payload["message"]
    assert "meeting outcome staff screens can now capture motions" in payload["message"]
    assert "minutes draft staff screens can now create citation-gated draft records" in payload["message"]
    assert "public archive staff screens can now publish public-safe records" in payload["message"]
    assert "connector import staff screens can now normalize local agenda-platform exports" in payload["message"]
    assert "packet export staff screens can now create records-ready bundles" in payload["message"]
    assert payload["next_step"] == "Production-depth consolidation and next CivicSuite module planning"


@pytest.mark.asyncio
async def test_health_endpoint_is_actionable_for_it_staff() -> None:
    module = load_app_module()
    async with AsyncClient(
        transport=ASGITransport(app=module.app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "service": "civicclerk",
        "version": "0.1.12",
        "civiccore": "0.16.0",
    }


def test_ci_runs_pytest_docs_and_placeholder_gates() -> None:
    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "python -m pytest" in text
    assert "bash scripts/verify-docs.sh" in text
    assert "python scripts/check-civiccore-placeholder-imports.py" in text


def test_placeholder_import_gate_passes_for_runtime_source() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check-civiccore-placeholder-imports.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PLACEHOLDER-IMPORT-CHECK: PASSED" in result.stdout


def test_current_facing_docs_describe_runtime_foundation_honestly() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "README.txt": (ROOT / "README.txt").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "USER-MANUAL.txt": (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        assert "runtime foundation" in text.lower(), f"{path} must mention the shipped foundation."
        assert "not installable yet" not in text.lower(), f"{path} must not retain pre-runtime scaffold wording."

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "runtime foundation" in changelog.lower()
