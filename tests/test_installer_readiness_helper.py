from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.13"


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
        "scripts/check_enterprise_installer_signing.py",
        "scripts/check_connector_sync_readiness.py",
        "scripts/run_connector_import_sync.py",
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


def test_installer_readiness_passes_complete_handoff_inputs(tmp_path: Path) -> None:
    dist_root, bundle = _write_installer_inputs(tmp_path)

    result = subprocess.run(
        [
            "python",
            "scripts/check_installer_readiness.py",
            "--dist-root",
            str(dist_root),
            "--bundle",
            str(bundle),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "installer_ready=true" in result.stdout
    assert "[PASS] checksums" in result.stdout
    assert "[PASS] handoff bundle entries" in result.stdout
    assert "INSTALLER-READINESS: PASSED" in result.stdout


def test_installer_readiness_fails_without_handoff_bundle(tmp_path: Path) -> None:
    dist_root, bundle = _write_installer_inputs(tmp_path)
    bundle.unlink()

    result = subprocess.run(
        [
            "python",
            "scripts/check_installer_readiness.py",
            "--dist-root",
            str(dist_root),
            "--bundle",
            str(bundle),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "installer_ready=false" in result.stdout
    assert "release handoff bundle is missing" in result.stdout
    assert "INSTALLER-READINESS: FAILED" in result.stdout


def test_installer_readiness_fails_checksum_mismatch(tmp_path: Path) -> None:
    dist_root, bundle = _write_installer_inputs(tmp_path)
    (dist_root / f"civicclerk-{VERSION}.tar.gz").write_text("tampered\n", encoding="utf-8")

    result = subprocess.run(
        [
            "python",
            "scripts/check_installer_readiness.py",
            "--dist-root",
            str(dist_root),
            "--bundle",
            str(bundle),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "checksum mismatch" in result.stdout
    assert "INSTALLER-READINESS: FAILED" in result.stdout


def test_installer_readiness_print_only_documents_plan() -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/check_installer_readiness.py",
            "--print-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for expected in [
        "CivicClerk installer readiness",
        "Confirm verify-release.sh produced the wheel",
        "Confirm SHA256SUMS.txt matches",
        "Confirm the release handoff zip exists",
        "Not an installer",
    ]:
        assert expected in result.stdout
