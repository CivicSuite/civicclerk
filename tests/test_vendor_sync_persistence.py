from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app
from civicclerk.vendor_live_sync import VendorSyncRunResult
from civicclerk.vendor_sync_persistence import VendorSyncConfigError, VendorSyncRepository


def _db_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path}"


def test_vendor_sync_source_persists_across_repository_instances(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path / "vendor-sync.db")
    repository = VendorSyncRepository(db_url=db_url)

    source = repository.create_source(
        connector="Legistar",
        source_name="Legistar production",
        source_url="https://vendor.example.gov/api/meetings",
        auth_method="bearer_token",
    )

    reloaded = VendorSyncRepository(db_url=db_url).get_source(source.id)
    assert reloaded is not None
    assert reloaded.connector == "legistar"
    assert reloaded.source_name == "Legistar production"
    assert reloaded.last_success_cursor_at is None
    assert reloaded.public_dict()["health_status"] == "healthy"
    assert reloaded.public_dict()["last_success_cursor_at"] is None


def test_vendor_sync_source_validation_error_is_actionable(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))

    with pytest.raises(VendorSyncConfigError) as exc_info:
        repository.create_source(
            connector="legistar",
            source_name="Bad private URL",
            source_url="http://127.0.0.1/api",
            auth_method="bearer_token",
        )

    public = exc_info.value.public_dict()
    assert public["message"] == "Vendor live-sync source configuration is not ready."
    assert public["fix"] == "Fix each failed readiness check, then save the source again."
    assert any(check["name"] == "source URL" and check["status"] == "FAIL" for check in public["checks"])


def test_vendor_sync_failed_runs_persist_circuit_open_state(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source = repository.create_source(
        connector="granicus",
        source_name="Granicus production",
        source_url="https://vendor.example.gov/api/meetings",
        auth_method="api_key",
    )

    updated = source
    for _ in range(5):
        recorded = repository.record_run(
            source_id=source.id,
            result=VendorSyncRunResult(
                records_discovered=1,
                records_succeeded=0,
                records_failed=1,
                error_summary="Vendor returned 503.",
            ),
        )
        assert recorded is not None
        updated, _ = recorded

    reloaded = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db")).get_source(source.id)
    assert reloaded is not None
    assert updated.sync_paused is True
    assert reloaded.consecutive_failure_count == 5
    assert reloaded.active_failure_count == 5
    assert reloaded.public_dict()["health_status"] == "circuit_open"
    assert len(repository.list_runs(source.id)) == 5


def test_vendor_sync_success_resets_active_failures(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source = repository.create_source(
        connector="primegov",
        source_name="PrimeGov production",
        source_url="https://vendor.example.gov/api/meetings",
        auth_method="oauth_client_credentials",
    )
    repository.record_run(
        source_id=source.id,
        result=VendorSyncRunResult(
            records_discovered=1,
            records_succeeded=0,
            records_failed=1,
            error_summary="Timeout.",
        ),
    )

    recorded = repository.record_run(
        source_id=source.id,
        result=VendorSyncRunResult(records_discovered=3, records_succeeded=3, records_failed=0),
    )

    assert recorded is not None
    updated, run = recorded
    assert run.status == "success"
    assert updated.consecutive_failure_count == 0
    assert updated.active_failure_count == 0
    assert updated.public_dict()["health_status"] == "healthy"


def test_vendor_sync_success_cursor_advances_only_when_requested(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source = repository.create_source(
        connector="legistar",
        source_name="Legistar production",
        source_url="https://vendor.example.gov/api/meetings",
        auth_method="bearer_token",
    )
    cursor = datetime(2026, 5, 2, 15, 30, tzinfo=UTC)

    unchanged = repository.record_run(
        source_id=source.id,
        result=VendorSyncRunResult(records_discovered=1, records_succeeded=1, records_failed=0),
    )
    assert unchanged is not None
    assert unchanged[0].last_success_cursor_at is None

    advanced = repository.record_run(
        source_id=source.id,
        result=VendorSyncRunResult(records_discovered=1, records_succeeded=1, records_failed=0),
        advance_success_cursor=True,
        cursor_at=cursor,
    )

    assert advanced is not None
    assert advanced[0].last_success_cursor_at == cursor
    assert advanced[0].public_dict()["last_success_cursor_at"] == "2026-05-02T15:30:00+00:00"


def test_vendor_sync_success_cursor_can_be_reset_for_reconciliation(tmp_path: Path) -> None:
    repository = VendorSyncRepository(db_url=_db_url(tmp_path / "vendor-sync.db"))
    source = repository.create_source(
        connector="legistar",
        source_name="Legistar production",
        source_url="https://vendor.example.gov/api/meetings",
        auth_method="bearer_token",
    )
    cursor = datetime(2026, 5, 2, 15, 30, tzinfo=UTC)
    repository.record_run(
        source_id=source.id,
        result=VendorSyncRunResult(records_discovered=2, records_succeeded=2, records_failed=0),
        advance_success_cursor=True,
        cursor_at=cursor,
    )

    reset = repository.reset_success_cursor(
        source_id=source.id,
        reset_reason="Force full reconciliation after vendor backfill.",
    )

    assert reset is not None
    reset_source, reset_event = reset
    assert reset_source.last_success_cursor_at is None
    assert reset_source.public_dict()["last_success_cursor_at"] is None
    assert reset_event.status == "cursor_reset"
    assert reset_event.error_summary == "Force full reconciliation after vendor backfill."
    assert repository.list_runs(source.id)[0].status == "cursor_reset"
    assert repository.list_runs(source.id)[0].error_summary == "Force full reconciliation after vendor backfill."


@pytest.mark.asyncio
async def test_vendor_live_sync_source_api_records_run_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CIVICCLERK_VENDOR_SYNC_DB_URL", _db_url(tmp_path / "vendor-sync-api.db"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/vendor-live-sync/sources",
            json={
                "connector": "legistar",
                "source_name": "Legistar production",
                "source_url": "https://vendor.example.gov/api/meetings",
                "auth_method": "bearer_token",
            },
        )
        source_id = created.json()["id"]
        final = None
        for _ in range(5):
            final = await client.post(
                f"/vendor-live-sync/sources/{source_id}/run-log",
                json={
                    "records_discovered": 1,
                    "records_succeeded": 0,
                    "records_failed": 1,
                    "error_summary": "Vendor API unavailable.",
                },
            )
        listed = await client.get("/vendor-live-sync/sources")
        runs = await client.get(f"/vendor-live-sync/sources/{source_id}/run-log")

    assert created.status_code == 201
    assert created.json()["network_calls"] is False
    assert final is not None
    assert final.status_code == 201
    assert final.json()["network_calls"] is False
    assert final.json()["source"]["health_status"] == "circuit_open"
    assert final.json()["run"]["status"] == "failed"
    assert listed.json()["sources"][0]["health_status"] == "circuit_open"
    assert runs.json()["network_calls"] is False
    assert len(runs.json()["runs"]) == 5


@pytest.mark.asyncio
async def test_vendor_live_sync_cursor_reset_api_is_actionable_and_network_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CIVICCLERK_VENDOR_SYNC_DB_URL", _db_url(tmp_path / "vendor-sync-api.db"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/vendor-live-sync/sources",
            json={
                "connector": "legistar",
                "source_name": "Legistar production",
                "source_url": "https://vendor.example.gov/api/meetings",
                "auth_method": "bearer_token",
            },
        )
        source_id = created.json()["id"]
        reset = await client.post(
            f"/vendor-live-sync/sources/{source_id}/cursor-reset",
            json={"cursor_at": None, "reason": "Force full reconciliation after vendor backfill."},
        )

    assert reset.status_code == 200
    body = reset.json()
    assert body["network_calls"] is False
    assert body["source"]["last_success_cursor_at"] is None
    assert body["message"] == "Vendor sync cursor cleared. The next enabled pull will run a full source reconciliation."
    assert body["fix"] == "Run connector readiness first, confirm credentials are current, then start the controlled pull window."
    assert body["reason_recorded"] == "Force full reconciliation after vendor backfill."
    assert body["reset_event"]["status"] == "cursor_reset"
    assert body["reset_event"]["error_summary"] == "Force full reconciliation after vendor backfill."


@pytest.mark.asyncio
async def test_vendor_live_sync_source_api_returns_actionable_config_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CIVICCLERK_VENDOR_SYNC_DB_URL", _db_url(tmp_path / "vendor-sync-api.db"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/vendor-live-sync/sources",
            json={
                "connector": "legistar",
                "source_name": "Bad source",
                "source_url": "http://127.0.0.1/api",
                "auth_method": "bearer_token",
            },
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["fix"] == "Fix each failed readiness check, then save the source again."
    assert any(check["name"] == "source URL" and check["status"] == "FAIL" for check in detail["checks"])


@pytest.mark.asyncio
async def test_vendor_live_sync_run_log_missing_source_is_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CIVICCLERK_VENDOR_SYNC_DB_URL", _db_url(tmp_path / "vendor-sync-api.db"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/vendor-live-sync/sources/missing/run-log",
            json={"records_discovered": 0, "records_succeeded": 0, "records_failed": 0},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "message": "Vendor live-sync source not found.",
        "fix": "Create the source with POST /vendor-live-sync/sources before recording a run outcome.",
    }
