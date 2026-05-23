from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.2"


def _bundle_entries(version: str) -> tuple[str, ...]:
    return (
        "README.md",
        "README.txt",
        "USER-MANUAL.md",
        "USER-MANUAL.txt",
        "CHANGELOG.md",
        "LICENSE",
        "docs/index.html",
        "docs/examples/deployment.env.example",
        "docs/examples/trusted-header-nginx.conf",
        "scripts/check_installer_readiness.py",
        "scripts/check_pilot_readiness.py",
        "scripts/check_enterprise_installer_signing.py",
        "scripts/check_connector_sync_readiness.py",
        "scripts/check_vendor_live_sync_readiness.py",
        "scripts/run_mock_city_environment_suite.py",
        "scripts/run_connector_import_sync.py",
        "scripts/run_vendor_live_sync.py",
        "scripts/start_fresh_install_rehearsal.ps1",
        "scripts/start_fresh_install_rehearsal.sh",
        "scripts/check_backup_restore_rehearsal.py",
        "scripts/check_protected_deployment_smoke.py",
        "scripts/start_backup_restore_rehearsal.ps1",
        "scripts/start_backup_restore_rehearsal.sh",
        "scripts/start_protected_demo_rehearsal.ps1",
        "scripts/start_protected_demo_rehearsal.sh",
        "scripts/local_trusted_header_proxy.py",
        f"dist/civicclerk-{version}-py3-none-any.whl",
        f"dist/civicclerk-{version}.tar.gz",
        "dist/SHA256SUMS.txt",
    )


def _write_installer_inputs(tmp_path: Path) -> tuple[Path, Path]:
    dist_root = tmp_path / "dist"
    dist_root.mkdir()
    wheel = dist_root / f"civicclerk-{VERSION}-py3-none-any.whl"
    sdist = dist_root / f"civicclerk-{VERSION}.tar.gz"
    wheel.write_text("wheel\n", encoding="utf-8")
    sdist.write_text("sdist\n", encoding="utf-8")
    (dist_root / "SHA256SUMS.txt").write_text(
        "\n".join(
            [
                f"{sha256(wheel.read_bytes()).hexdigest()}  {wheel.name}",
                f"{sha256(sdist.read_bytes()).hexdigest()}  {sdist.name}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    bundle = dist_root / f"civicclerk-{VERSION}-release-handoff.zip"
    with zipfile.ZipFile(bundle, mode="w") as archive:
        for entry in _bundle_entries(VERSION):
            archive.writestr(entry, "test input\n")
    return dist_root, bundle


def test_pilot_readiness_is_developer_ready_with_adversarial_mocks(tmp_path: Path) -> None:
    dist_root, bundle = _write_installer_inputs(tmp_path)
    report = tmp_path / "pilot-readiness.json"

    result = subprocess.run(
        [
            "python",
            "scripts/check_pilot_readiness.py",
            "--dist-root",
            str(dist_root),
            "--bundle",
            str(bundle),
            "--output",
            str(report),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "developer_ready=true" in result.stdout
    assert "proof_model=adversarial_mock_validation" in result.stdout
    assert "external_dependencies_pending=false" in result.stdout
    assert "[PASS] installer checksums" in result.stdout
    assert "[PASS] mock city vendor contract suite" in result.stdout
    assert "[PASS] mock city municipal IdP contract suite" in result.stdout
    assert "[PASS] mock city backup retention contract suite" in result.stdout
    assert "[PASS] unsigned installer warning docs" in result.stdout
    assert "PILOT-READINESS: DEVELOPER-READY" in result.stdout
    assert '"developer_ready": true' in report.read_text(encoding="utf-8")
    assert '"proof_model": "adversarial_mock_validation"' in report.read_text(encoding="utf-8")


def test_pilot_readiness_strict_adversarial_mock_gate_passes_when_mocks_pass(tmp_path: Path) -> None:
    dist_root, bundle = _write_installer_inputs(tmp_path)

    result = subprocess.run(
        [
            "python",
            "scripts/check_pilot_readiness.py",
            "--dist-root",
            str(dist_root),
            "--bundle",
            str(bundle),
            "--require-adversarial-mocks",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "developer_ready=true" in result.stdout
    assert "external_dependencies_pending=false" in result.stdout


def test_pilot_readiness_print_only_documents_adversarial_proof_model() -> None:
    result = subprocess.run(
        ["python", "scripts/check_pilot_readiness.py", "--print-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Developer-owned checks:" in result.stdout
    assert "Mock city municipal IdP contracts pass without contacting an IdP." in result.stdout
    assert "Mock city backup retention/off-host contracts pass without contacting storage providers." in result.stdout
    assert "Release proof model:" in result.stdout
    assert "no external deployment proofs are required" in result.stdout
    assert "adversarial mock-city vendor, municipal IdP, protected-auth, and backup-retention suites are release gates" in result.stdout
