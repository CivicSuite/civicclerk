from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from civicclerk.vendor_network_sync import NETWORK_ENABLED_ENV_VAR, run_vendor_network_sync
from civicclerk.vendor_live_sync import VendorSyncRunResult
from civicclerk.vendor_sync_persistence import VendorSyncRepository


ROOT = Path(__file__).resolve().parents[1]

LEGISTAR_PAYLOAD = {
    "MeetingId": "leg-200",
    "MeetingName": "Council Regular Meeting",
    "MeetingDate": "2026-05-06T18:30:00Z",
    "AgendaItems": [
        {"FileNumber": "24-001", "Title": "Approve minutes", "DepartmentName": "Clerk"}
    ],
}


def _db_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path}"


def _source(repository: VendorSyncRepository) -> str:
    return repository.create_source(
        connector="legistar",
        source_name="Legistar production",
        source_url="https://vendor.example.gov/api/meetings",
        auth_method="bearer_token",
    ).id


def test_vendor_network_sync_requires_explicit_network_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(NETWORK_ENABLED_ENV_VAR, raising=False)
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source_id = _source(repository)
    output = tmp_path / "blocked-report.json"

    report = run_vendor_network_sync(repository=repository, source_id=source_id, output_path=output)

    assert report.network_calls is False
    assert report.records_discovered == 0
    assert NETWORK_ENABLED_ENV_VAR in report.fix
    assert repository.list_runs(source_id) == []
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["network_calls"] is False
    assert saved["records_failed"] == 0


def test_vendor_network_sync_fetches_normalizes_and_records_success(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source_id = _source(repository)
    observed_headers: dict[str, str] = {}

    def fake_fetch(source, headers, timeout_seconds):
        assert source.source_url == "https://vendor.example.gov/api/meetings"
        assert timeout_seconds == 20
        observed_headers.update(headers)
        return [LEGISTAR_PAYLOAD]

    report = run_vendor_network_sync(
        repository=repository,
        source_id=source_id,
        enable_network=True,
        auth_secret="secret-token",
        fetch_json=fake_fetch,
    )

    assert report.network_calls is True
    assert report.records_discovered == 1
    assert report.records_succeeded == 1
    assert report.records_failed == 0
    assert report.run_status == "success"
    assert report.source_health_status == "healthy"
    assert report.delta_request_url == "https://vendor.example.gov/api/meetings"
    assert report.cursor_param == "LastModifiedDate"
    assert report.cursor_value is None
    assert report.cursor_advanced_at is not None
    assert report.attempts[0].external_meeting_id == "leg-200"
    assert observed_headers == {"Authorization": "Bearer secret-token"}
    assert repository.list_runs(source_id)[0].status == "success"
    assert repository.get_source(source_id).last_success_cursor_at is not None


def test_vendor_network_sync_advances_cursor_to_request_start_not_finish(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source_id = _source(repository)
    request_started_at: datetime | None = None

    def fake_fetch(source, headers, timeout_seconds):
        nonlocal request_started_at
        request_started_at = datetime.now(UTC)
        return [LEGISTAR_PAYLOAD]

    run_vendor_network_sync(
        repository=repository,
        source_id=source_id,
        enable_network=True,
        auth_secret="secret-token",
        fetch_json=fake_fetch,
    )

    assert request_started_at is not None
    cursor = repository.get_source(source_id).last_success_cursor_at
    assert cursor is not None
    assert cursor <= request_started_at


def test_vendor_network_sync_uses_persisted_cursor_for_delta_request(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source_id = _source(repository)
    repository.record_run(
        source_id=source_id,
        result=VendorSyncRunResult(records_discovered=1, records_succeeded=1, records_failed=0),
        advance_success_cursor=True,
    )
    requested_urls: list[str] = []

    def fake_fetch(source, headers, timeout_seconds):
        requested_urls.append(source.source_url)
        return [LEGISTAR_PAYLOAD]

    report = run_vendor_network_sync(
        repository=repository,
        source_id=source_id,
        enable_network=True,
        auth_secret="secret-token",
        fetch_json=fake_fetch,
    )

    assert report.records_failed == 0
    assert "LastModifiedDate=" in requested_urls[0]
    assert requested_urls[0] == report.delta_request_url
    assert report.cursor_value is not None
    assert report.cursor_advanced_at is not None


def test_vendor_network_sync_missing_secret_is_recorded_without_claiming_network_call(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source_id = _source(repository)
    output = tmp_path / "missing-secret-report.json"

    report = run_vendor_network_sync(
        repository=repository,
        source_id=source_id,
        enable_network=True,
        fetch_json=lambda *_: [LEGISTAR_PAYLOAD],
        output_path=output,
    )

    assert report.network_calls is False
    assert report.records_failed == 1
    assert "credentials are required" in report.message
    assert "deployment secret" in report.fix
    assert repository.list_runs(source_id)[0].status == "failed"
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["network_calls"] is False
    assert saved["records_failed"] == 1
    assert "credentials are required" in saved["message"]


def test_vendor_network_sync_records_actionable_failures_and_opens_circuit(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source_id = _source(repository)

    for _ in range(5):
        report = run_vendor_network_sync(
            repository=repository,
            source_id=source_id,
            enable_network=True,
            auth_secret="secret-token",
            fetch_json=lambda *_: {"MeetingId": "leg-200", "AgendaItems": []},
        )

    assert report.records_failed == 1
    assert report.run_status == "failed"
    assert report.source_health_status == "circuit_open"
    assert "MeetingName" in report.message
    assert "MeetingName" in report.attempts[0].message
    assert len(repository.list_runs(source_id)) == 5

    blocked = run_vendor_network_sync(
        repository=repository,
        source_id=source_id,
        enable_network=True,
        auth_secret="secret-token",
        fetch_json=lambda *_: [LEGISTAR_PAYLOAD],
    )
    assert blocked.network_calls is False
    assert "circuit breaker is open" in blocked.message


def test_vendor_network_sync_cli_print_only_is_safe() -> None:
    result = subprocess.run(
        ["python", "scripts/run_vendor_live_sync.py", "--source-id", "example-source", "--print-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Network calls: disabled in print-only mode" in result.stdout
    assert "Re-validate the source URL" in result.stdout
    assert "last successful source cursor" in result.stdout
    assert "never from the source URL" in result.stdout


def test_vendor_network_sync_writes_report_without_secrets(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source_id = _source(repository)
    output = tmp_path / "vendor-sync-report.json"

    run_vendor_network_sync(
        repository=repository,
        source_id=source_id,
        enable_network=True,
        auth_secret="secret-token",
        fetch_json=lambda *_: [LEGISTAR_PAYLOAD],
        output_path=output,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["records_succeeded"] == 1
    assert report["cursor_advanced_at"] is not None
    assert "secret-token" not in output.read_text(encoding="utf-8")
