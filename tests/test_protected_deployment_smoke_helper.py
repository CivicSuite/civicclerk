from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.17"
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
    env = __import__("os").environ.copy()
    for name in DEPLOYMENT_ENV_VARS:
        env.pop(name, None)
    return env


def _write_completed_profile(tmp_path: Path) -> Path:
    dist_root = tmp_path / "dist"
    dist_root.mkdir()
    for name in [
        f"civicclerk-{VERSION}-py3-none-any.whl",
        f"civicclerk-{VERSION}.tar.gz",
        "SHA256SUMS.txt",
    ]:
        (dist_root / name).write_text("test artifact\n", encoding="utf-8")

    profile = tmp_path / "deployment.env"
    profile.write_text(
        "\n".join(
            [
                "CIVICCLERK_STAFF_AUTH_MODE=bearer",
                "CIVICCLERK_STAFF_AUTH_TOKEN_ROLES='{\"secret-smoke-token\":[\"clerk_admin\",\"meeting_editor\"]}'",
                f"CIVICCLERK_AGENDA_INTAKE_DB_URL=sqlite:///{tmp_path / 'intake.db'}",
                f"CIVICCLERK_AGENDA_ITEM_DB_URL=sqlite:///{tmp_path / 'items.db'}",
                f"CIVICCLERK_MEETING_DB_URL=sqlite:///{tmp_path / 'meetings.db'}",
                f"CIVICCLERK_PACKET_ASSEMBLY_DB_URL=sqlite:///{tmp_path / 'packet.db'}",
                f"CIVICCLERK_NOTICE_CHECKLIST_DB_URL=sqlite:///{tmp_path / 'notice.db'}",
                f"CIVICCLERK_EXPORT_ROOT={tmp_path / 'exports'}",
                f"CIVICCLERK_DEPLOYMENT_PREFLIGHT_DIST_ROOT={dist_root}",
            ]
        ),
        encoding="utf-8",
    )
    return profile


def _write_completed_trusted_header_profile(tmp_path: Path) -> Path:
    dist_root = tmp_path / "dist"
    dist_root.mkdir()
    for name in [
        f"civicclerk-{VERSION}-py3-none-any.whl",
        f"civicclerk-{VERSION}.tar.gz",
        "SHA256SUMS.txt",
    ]:
        (dist_root / name).write_text("test artifact\n", encoding="utf-8")

    profile = tmp_path / "trusted-header-deployment.env"
    profile.write_text(
        "\n".join(
            [
                "CIVICCLERK_STAFF_AUTH_MODE=trusted_header",
                "CIVICCLERK_STAFF_SSO_PROVIDER=Test SSO",
                "CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER=X-CivicClerk-Staff-Email",
                "CIVICCLERK_STAFF_SSO_ROLES_HEADER=X-CivicClerk-Staff-Roles",
                "CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES=127.0.0.1/32",
                f"CIVICCLERK_AGENDA_INTAKE_DB_URL=sqlite:///{tmp_path / 'intake.db'}",
                f"CIVICCLERK_AGENDA_ITEM_DB_URL=sqlite:///{tmp_path / 'items.db'}",
                f"CIVICCLERK_MEETING_DB_URL=sqlite:///{tmp_path / 'meetings.db'}",
                f"CIVICCLERK_PACKET_ASSEMBLY_DB_URL=sqlite:///{tmp_path / 'packet.db'}",
                f"CIVICCLERK_NOTICE_CHECKLIST_DB_URL=sqlite:///{tmp_path / 'notice.db'}",
                f"CIVICCLERK_EXPORT_ROOT={tmp_path / 'exports'}",
                f"CIVICCLERK_DEPLOYMENT_PREFLIGHT_DIST_ROOT={dist_root}",
            ]
        ),
        encoding="utf-8",
    )
    return profile


def test_protected_deployment_smoke_passes_completed_bearer_profile(tmp_path: Path) -> None:
    profile = _write_completed_profile(tmp_path)

    result = subprocess.run(
        [
            "python",
            "scripts/check_protected_deployment_smoke.py",
            "--env-file",
            str(profile),
        ],
        cwd=ROOT,
        env=_base_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PROTECTED-DEPLOYMENT-SMOKE: PASSED" in result.stdout
    assert "[PASS] session probe: 200" in result.stdout
    assert "[PASS] write probe: 201" in result.stdout
    assert "secret-smoke-token" not in result.stdout
    assert "Bearer <redacted>" in result.stdout


def test_protected_deployment_smoke_passes_completed_trusted_header_profile(tmp_path: Path) -> None:
    profile = _write_completed_trusted_header_profile(tmp_path)

    result = subprocess.run(
        [
            "python",
            "scripts/check_protected_deployment_smoke.py",
            "--env-file",
            str(profile),
            "--trusted-proxy-client-ip",
            "127.0.0.1",
        ],
        cwd=ROOT,
        env=_base_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "mode=trusted_header deployment_ready=true" in result.stdout
    assert "[PASS] session probe: 200" in result.stdout
    assert "[PASS] write probe: 201" in result.stdout


def test_protected_deployment_smoke_rejects_placeholder_example() -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/check_protected_deployment_smoke.py",
            "--env-file",
            "docs/examples/deployment.env.example",
        ],
        cwd=ROOT,
        env=_base_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "PROTECTED-DEPLOYMENT-SMOKE: FAILED" in result.stdout
    assert "deployment profile placeholders" in result.stdout
    assert "replace-with-secret-token" not in result.stdout


def test_protected_deployment_smoke_print_only_documents_steps(tmp_path: Path) -> None:
    profile = _write_completed_profile(tmp_path)

    result = subprocess.run(
        [
            "python",
            "scripts/check_protected_deployment_smoke.py",
            "--env-file",
            str(profile),
            "--print-only",
        ],
        cwd=ROOT,
        env=_base_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for expected in [
        "CivicClerk protected deployment smoke",
        "Run strict deployment readiness checks.",
        "GET /health.",
        "GET /staff/auth-readiness.",
        "Execute the returned protected session probe.",
        "Execute the returned protected write probe.",
    ]:
        assert expected in result.stdout
    assert "secret-smoke-token" not in result.stdout
