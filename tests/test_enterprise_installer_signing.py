from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.16"


def test_enterprise_installer_signing_print_only_explains_inputs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_enterprise_installer_signing.py", "--print-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "CivicClerk enterprise installer signing readiness" in result.stdout
    assert "CIVICCLERK_SIGNTOOL_PATH" in result.stdout
    assert "CIVICCLERK_SIGNING_CERT_SHA1" in result.stdout
    assert "CIVICCLERK_SIGNING_PFX_PASSWORD_ENV" in result.stdout
    assert "No secrets are printed" in result.stdout


def test_enterprise_installer_signing_fails_actionably_without_cert_inputs(tmp_path: Path) -> None:
    artifact = tmp_path / f"CivicClerk-{VERSION}-Setup.exe"
    artifact.write_bytes(b"unsigned installer")
    env = os.environ.copy()
    env["PATH"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/check_enterprise_installer_signing.py", "--artifact", str(artifact)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "signing_ready=false" in result.stdout
    assert "setup executable exists" in result.stdout
    assert "Microsoft SignTool was not found" in result.stdout
    assert "no code-signing certificate identity is configured" in result.stdout
    assert "no timestamp authority URL is configured" in result.stdout
    assert "ENTERPRISE-INSTALLER-SIGNING: FAILED" in result.stdout


def test_enterprise_installer_signing_passes_with_redacted_certificate_contract(tmp_path: Path) -> None:
    artifact = tmp_path / f"CivicClerk-{VERSION}-Setup.exe"
    artifact.write_bytes(b"unsigned installer")
    signtool = tmp_path / "signtool.exe"
    signtool.write_text("fake signtool for readiness check\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "CIVICCLERK_SIGNTOOL_PATH": str(signtool),
            "CIVICCLERK_SIGNING_CERT_SHA1": "00ABCDEF",
            "CIVICCLERK_SIGNING_TIMESTAMP_URL": "https://timestamp.example.test",
        }
    )

    result = subprocess.run(
        [sys.executable, "scripts/check_enterprise_installer_signing.py", "--artifact", str(artifact)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "signing_ready=true" in result.stdout
    assert "CIVICCLERK_SIGNING_CERT_SHA1 is set" in result.stdout
    assert "00ABCDEF" not in result.stdout
    assert "ENTERPRISE-INSTALLER-SIGNING: PASSED" in result.stdout
