"""Backup/restore rehearsal helper contract tests."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_backup_restore_rehearsal_verifier_creates_and_verifies_restored_stores(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/check_backup_restore_rehearsal.py",
            "--rehearsal-root",
            str(tmp_path),
            "--run-id",
            "contract-run",
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BACKUP-RESTORE-REHEARSAL: PASSED" in result.stdout
    run_root = tmp_path / "contract-run"
    manifest_path = run_root / "backup" / "civicclerk-backup-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["service"] == "civicclerk"
    assert len(manifest["stores"]) == 5
    assert (run_root / "restored-data" / "agenda-intake.db").exists()
    assert (run_root / "restored-exports" / "backup-restore-rehearsal-packet" / "manifest.json").exists()


def test_backup_restore_rehearsal_verifier_prints_operator_plan(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/check_backup_restore_rehearsal.py",
            "--rehearsal-root",
            str(tmp_path),
            "--run-id",
            "print-plan",
            "--print-only",
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for expected in [
        "CivicClerk backup/restore rehearsal",
        "Backup manifest: backup/civicclerk-backup-manifest.json",
        "CIVICCLERK_AGENDA_INTAKE_DB_URL=",
        "CIVICCLERK_AGENDA_ITEM_DB_URL=",
        "CIVICCLERK_MEETING_DB_URL=",
        "CIVICCLERK_PACKET_ASSEMBLY_DB_URL=",
        "CIVICCLERK_NOTICE_CHECKLIST_DB_URL=",
        "CIVICCLERK_EXPORT_ROOT=",
        "If a check fails:",
    ]:
        assert expected in result.stdout


def test_backup_restore_rehearsal_powershell_wrapper_prints_expected_plan() -> None:
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell runtime is not available in this environment.")

    result = subprocess.run(
        [
            shell,
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "start_backup_restore_rehearsal.ps1"),
            "-PrintOnly",
            "-RunId",
            "print-plan",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for expected in [
        "CivicClerk backup/restore rehearsal profile",
        "Run id: print-plan",
        "Python verifier: python scripts/check_backup_restore_rehearsal.py",
        "Backup manifest: backup\\civicclerk-backup-manifest.json",
        "Restored stores: restored-data\\*.db",
        "Fix path:",
    ]:
        assert expected in result.stdout


def test_backup_restore_rehearsal_bash_wrapper_prints_expected_plan() -> None:
    shell = shutil.which("bash")
    if shell is None:
        pytest.skip("Bash runtime is not available in this environment.")

    result = subprocess.run(
        [
            shell,
            "scripts/start_backup_restore_rehearsal.sh",
            "--print-only",
            "--run-id",
            "print-plan",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    for expected in [
        "CivicClerk backup/restore rehearsal profile",
        "Run id: print-plan",
        "Python verifier: python scripts/check_backup_restore_rehearsal.py",
        "Backup manifest: backup/civicclerk-backup-manifest.json",
        "Restored stores: restored-data/*.db",
        "Fix path:",
    ]:
        assert expected in result.stdout


def test_docs_reference_backup_restore_rehearsal_helper() -> None:
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
        "scripts/start_backup_restore_rehearsal.ps1",
        "scripts/start_backup_restore_rehearsal.sh",
        "scripts/check_backup_restore_rehearsal.py",
        ".backup-restore-rehearsal",
        "civicclerk-backup-manifest.json",
        "CIVICCLERK_NOTICE_CHECKLIST_DB_URL",
    ]:
        assert expected in docs
