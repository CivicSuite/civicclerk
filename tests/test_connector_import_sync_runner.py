from __future__ import annotations

import json
from pathlib import Path
import subprocess


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
