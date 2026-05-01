from __future__ import annotations

import json
from pathlib import Path
import subprocess

from civicclerk.worker import (
    CONNECTOR_SYNC_CONNECTORS_ENV_VAR,
    CONNECTOR_SYNC_ENABLED_ENV_VAR,
    CONNECTOR_SYNC_LEDGER_PATH_ENV_VAR,
    CONNECTOR_SYNC_PAYLOAD_DIR_ENV_VAR,
    connector_import_sync,
)


ROOT = Path(__file__).resolve().parents[1]


def test_connector_import_sync_runner_writes_normalized_ledger(tmp_path: Path) -> None:
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    (payload_dir / "granicus.json").write_text(
        json.dumps(
            {
                "id": "gr-100",
                "name": "Budget Hearing",
                "start": "2026-05-05T19:00:00Z",
                "agenda": [{"id": "gr-item-1", "title": "Adopt budget ordinance", "department": "Finance"}],
            }
        ),
        encoding="utf-8",
    )
    ledger = tmp_path / "connector-import-ledger.json"

    result = subprocess.run(
        [
            "python",
            "scripts/run_connector_import_sync.py",
            "--payload-dir",
            str(payload_dir),
            "--connector",
            "granicus",
            "--output",
            str(ledger),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "network_calls=false" in result.stdout
    assert "imported_count=1" in result.stdout
    assert "CONNECTOR-IMPORT-SYNC: PASSED" in result.stdout
    records = json.loads(ledger.read_text(encoding="utf-8"))
    assert records[0]["ok"] is True
    assert records[0]["normalized"]["source_provenance"] == {
        "connector": "granicus",
        "imported_from": "local_payload",
        "external_meeting_id": "gr-100",
    }


def test_connector_import_sync_runner_reports_actionable_failures(tmp_path: Path) -> None:
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    (payload_dir / "legistar.json").write_text(
        json.dumps({"MeetingId": "leg-200", "AgendaItems": []}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "python",
            "scripts/run_connector_import_sync.py",
            "--payload-dir",
            str(payload_dir),
            "--connector",
            "legistar",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "failed_count=1" in result.stdout
    assert "Legistar meeting payload is missing required field MeetingName." in result.stdout
    assert "Export the meeting again with MeetingName included" in result.stdout
    assert "CONNECTOR-IMPORT-SYNC: FAILED" in result.stdout


def test_connector_import_sync_runner_accepts_windows_utf8_bom_exports(tmp_path: Path) -> None:
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    (payload_dir / "granicus.json").write_text(
        json.dumps(
            {
                "id": "gr-bom",
                "name": "Windows Export Meeting",
                "start": "2026-05-06T19:00:00Z",
                "agenda": [{"id": "gr-item-bom", "title": "Review PowerShell export", "department": "IT"}],
            }
        ),
        encoding="utf-8-sig",
    )

    result = subprocess.run(
        [
            "python",
            "scripts/run_connector_import_sync.py",
            "--payload-dir",
            str(payload_dir),
            "--connector",
            "granicus",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "imported_count=1" in result.stdout
    assert "CONNECTOR-IMPORT-SYNC: PASSED" in result.stdout


def test_connector_import_sync_runner_print_only_is_honest(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "python",
            "scripts/run_connector_import_sync.py",
            "--payload-dir",
            str(tmp_path),
            "--connector",
            "primegov",
            "--print-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Network calls: disabled" in result.stdout
    assert "Not scheduled live sync" in result.stdout
    assert "existing CivicClerk connector import contract" in result.stdout


def test_scheduled_connector_import_sync_skips_until_enabled(monkeypatch) -> None:
    monkeypatch.delenv(CONNECTOR_SYNC_ENABLED_ENV_VAR, raising=False)

    result = connector_import_sync.run()

    assert result["skipped"] is True
    assert CONNECTOR_SYNC_ENABLED_ENV_VAR in result["fix"]


def test_scheduled_connector_import_sync_writes_ledger_without_network(monkeypatch, tmp_path: Path) -> None:
    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()
    (payload_dir / "granicus.json").write_text(
        json.dumps(
            {
                "id": "gr-300",
                "name": "Scheduled Budget Hearing",
                "start": "2026-05-12T19:00:00Z",
                "agenda": [{"id": "gr-item-7", "title": "Adopt budget", "department": "Finance"}],
            }
        ),
        encoding="utf-8",
    )
    ledger = tmp_path / "scheduled-ledger.json"
    monkeypatch.setenv(CONNECTOR_SYNC_ENABLED_ENV_VAR, "true")
    monkeypatch.setenv(CONNECTOR_SYNC_PAYLOAD_DIR_ENV_VAR, str(payload_dir))
    monkeypatch.setenv(CONNECTOR_SYNC_LEDGER_PATH_ENV_VAR, str(ledger))
    monkeypatch.setenv(CONNECTOR_SYNC_CONNECTORS_ENV_VAR, "granicus")

    result = connector_import_sync.run()

    assert result["skipped"] is False
    assert result["network_calls"] is False
    assert result["imported_count"] == 1
    assert result["failed_count"] == 0
    assert result["ledger"] == str(ledger)
    records = json.loads(ledger.read_text(encoding="utf-8"))
    assert records[0]["normalized"]["external_meeting_id"] == "gr-300"


def test_scheduled_connector_import_sync_writes_actionable_ledger_for_bad_connector(
    monkeypatch, tmp_path: Path
) -> None:
    ledger = tmp_path / "bad-connector-ledger.json"
    monkeypatch.setenv(CONNECTOR_SYNC_ENABLED_ENV_VAR, "true")
    monkeypatch.setenv(CONNECTOR_SYNC_PAYLOAD_DIR_ENV_VAR, str(tmp_path / "payloads"))
    monkeypatch.setenv(CONNECTOR_SYNC_LEDGER_PATH_ENV_VAR, str(ledger))
    monkeypatch.setenv(CONNECTOR_SYNC_CONNECTORS_ENV_VAR, "not-a-vendor")

    result = connector_import_sync.run()

    assert result["skipped"] is False
    assert result["network_calls"] is False
    assert result["imported_count"] == 0
    assert result["failed_count"] == 1
    records = json.loads(ledger.read_text(encoding="utf-8"))
    assert records[0]["ok"] is False
    assert records[0]["message"] == "Unsupported connector 'not-a-vendor'."
    assert "Use one of:" in records[0]["fix"]
