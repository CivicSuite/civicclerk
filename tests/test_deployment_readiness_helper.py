from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_ENV_VARS = (
    "CIVICCLERK_STAFF_AUTH_MODE",
    "CIVICCLERK_STAFF_AUTH_TOKEN_ROLES",
    "CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES",
    "CIVICCLERK_AGENDA_INTAKE_DB_URL",
    "CIVICCLERK_AGENDA_ITEM_DB_URL",
    "CIVICCLERK_MEETING_DB_URL",
    "CIVICCLERK_PACKET_ASSEMBLY_DB_URL",
    "CIVICCLERK_NOTICE_CHECKLIST_DB_URL",
    "CIVICCLERK_EXPORT_ROOT",
    "CIVICCLERK_DEPLOYMENT_PREFLIGHT_DIST_ROOT",
)


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in DEPLOYMENT_ENV_VARS:
        env.pop(name, None)
    return env


def test_deployment_readiness_helper_reports_local_rehearsal_as_not_deployment_ready() -> None:
    result = subprocess.run(
        ["python", "scripts/check_deployment_readiness.py"],
        cwd=ROOT,
        env=_base_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout
    assert "CivicClerk deployment readiness preflight" in output
    assert "deployment_ready=false" in output
    assert "[WARN] staff auth: open mode is ready for local rehearsal but not real staff deployment." in output
    assert "CIVICCLERK_STAFF_AUTH_MODE=bearer" in output
    assert "missing deployment database URLs" in output
    assert "values are intentionally not printed" not in output


def test_deployment_readiness_helper_strict_fails_when_not_deployment_ready() -> None:
    result = subprocess.run(
        ["python", "scripts/check_deployment_readiness.py", "--strict"],
        cwd=ROOT,
        env=_base_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "deployment_ready=false" in result.stdout


def test_deployment_readiness_helper_passes_configured_bearer_environment(tmp_path: Path) -> None:
    env = _base_env()
    dist_root = tmp_path / "dist"
    dist_root.mkdir()
    for name in [
        "civicclerk-0.1.11-py3-none-any.whl",
        "civicclerk-0.1.11.tar.gz",
        "SHA256SUMS.txt",
    ]:
        (dist_root / name).write_text("test artifact\n", encoding="utf-8")

    env.update(
        {
            "CIVICCLERK_STAFF_AUTH_MODE": "bearer",
            "CIVICCLERK_STAFF_AUTH_TOKEN_ROLES": '{"clerk-token":["clerk_admin","meeting_editor"]}',
            "CIVICCLERK_AGENDA_INTAKE_DB_URL": f"sqlite:///{tmp_path / 'intake.db'}",
            "CIVICCLERK_AGENDA_ITEM_DB_URL": f"sqlite:///{tmp_path / 'items.db'}",
            "CIVICCLERK_MEETING_DB_URL": f"sqlite:///{tmp_path / 'meetings.db'}",
            "CIVICCLERK_PACKET_ASSEMBLY_DB_URL": f"sqlite:///{tmp_path / 'packet.db'}",
            "CIVICCLERK_NOTICE_CHECKLIST_DB_URL": f"sqlite:///{tmp_path / 'notice.db'}",
            "CIVICCLERK_EXPORT_ROOT": str(tmp_path / "exports"),
            "CIVICCLERK_DEPLOYMENT_PREFLIGHT_DIST_ROOT": str(dist_root),
        }
    )

    result = subprocess.run(
        ["python", "scripts/check_deployment_readiness.py", "--strict"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout
    assert "deployment_ready=true" in output
    assert "[PASS] staff auth: bearer mode reports deployment_ready=true." in output
    assert "[PASS] persistent stores: all deployment database URL environment variables are set" in output
    assert "clerk-token" not in output
