from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.20"


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


def test_pilot_readiness_is_developer_ready_with_external_dependencies_pending(tmp_path: Path) -> None:
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
    assert "external_dependencies_pending=true" in result.stdout
    assert "[PASS] installer checksums" in result.stdout
    assert "[PASS] mock city vendor contract suite" in result.stdout
    assert "[PASS] mock city municipal IdP contract suite" in result.stdout
    assert "[PASS] mock city backup retention contract suite" in result.stdout
    assert "[PASS] unsigned installer warning docs" in result.stdout
    assert "[EXTERNAL] code-signing certificate" in result.stdout
    assert "PILOT-READINESS: DEVELOPER-READY" in result.stdout
    assert '"developer_ready": true' in report.read_text(encoding="utf-8")


def test_pilot_readiness_strict_external_proof_fails_until_city_proofs_exist(tmp_path: Path) -> None:
    dist_root, bundle = _write_installer_inputs(tmp_path)

    result = subprocess.run(
        [
            "python",
            "scripts/check_pilot_readiness.py",
            "--dist-root",
            str(dist_root),
            "--bundle",
            str(bundle),
            "--require-external-proof",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "developer_ready=true" in result.stdout
    assert "[EXTERNAL] municipal vendor API proof" in result.stdout


def test_pilot_readiness_passes_strict_when_external_proofs_are_attached(tmp_path: Path) -> None:
    dist_root, bundle = _write_installer_inputs(tmp_path)
    proofs = []
    for name in ["signing.txt", "idp.txt", "vendor.txt", "retention.txt"]:
        path = tmp_path / name
        path.write_text("redacted proof\n", encoding="utf-8")
        proofs.append(path)

    result = subprocess.run(
        [
            "python",
            "scripts/check_pilot_readiness.py",
            "--dist-root",
            str(dist_root),
            "--bundle",
            str(bundle),
            "--signing-proof",
            str(proofs[0]),
            "--idp-proof",
            str(proofs[1]),
            "--vendor-proof",
            str(proofs[2]),
            "--retention-proof",
            str(proofs[3]),
            "--require-external-proof",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "external_dependencies_pending=false" in result.stdout
    assert "[PASS] municipal IdP deployment proof" in result.stdout


def test_pilot_readiness_print_only_documents_external_proof_slots() -> None:
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
    assert "External proof slots:" in result.stdout
    assert "municipal vendor API live-sync proof" in result.stdout
