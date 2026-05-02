from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from civicclerk.vendor_network_sync import NETWORK_ENABLED_ENV_VAR
from civicclerk.worker import (
    VENDOR_NETWORK_SYNC_DB_URL_ENV_VAR,
    VENDOR_NETWORK_SYNC_REPORT_DIR_ENV_VAR,
    VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR,
    VENDOR_NETWORK_SYNC_SOURCE_IDS_ENV_VAR,
    vendor_network_sync,
)


@dataclass(frozen=True)
class FakeVendorNetworkReport:
    source_id: str
    network_calls: bool = True
    records_failed: int = 0
    run_status: str | None = "success"

    def public_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "connector": "legistar",
            "network_calls": self.network_calls,
            "records_discovered": 1,
            "records_succeeded": 1 if self.records_failed == 0 else 0,
            "records_failed": self.records_failed,
            "run_status": self.run_status,
            "source_health_status": "healthy" if self.records_failed == 0 else "degraded",
            "delta_request_url": "https://vendor.example.gov/api/meetings",
            "cursor_param": "LastModifiedDate",
            "cursor_value": None,
            "cursor_advanced_at": "2026-05-02T00:00:00+00:00",
            "message": "fake scheduled run",
            "fix": "fake fix",
            "attempts": [],
        }


def test_scheduled_vendor_network_sync_skips_until_enabled(monkeypatch) -> None:
    monkeypatch.delenv(VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR, raising=False)

    result = vendor_network_sync.run()

    assert result["skipped"] is True
    assert result["network_calls"] is False
    assert VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR in result["fix"]


def test_scheduled_vendor_network_sync_requires_global_network_gate(monkeypatch) -> None:
    monkeypatch.setenv(VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR, "true")
    monkeypatch.delenv(NETWORK_ENABLED_ENV_VAR, raising=False)

    result = vendor_network_sync.run()

    assert result["skipped"] is True
    assert result["network_calls"] is False
    assert NETWORK_ENABLED_ENV_VAR in result["fix"]


def test_scheduled_vendor_network_sync_runs_configured_sources(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run_vendor_network_sync(**kwargs):
        calls.append(kwargs)
        return FakeVendorNetworkReport(source_id=kwargs["source_id"])

    monkeypatch.setattr("civicclerk.worker.run_vendor_network_sync", fake_run_vendor_network_sync)
    monkeypatch.setenv(VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR, "true")
    monkeypatch.setenv(NETWORK_ENABLED_ENV_VAR, "true")
    monkeypatch.setenv(VENDOR_NETWORK_SYNC_SOURCE_IDS_ENV_VAR, "source-1,source/2")
    monkeypatch.setenv(VENDOR_NETWORK_SYNC_DB_URL_ENV_VAR, f"sqlite+pysqlite:///{tmp_path / 'vendor-sync.db'}")
    monkeypatch.setenv(VENDOR_NETWORK_SYNC_REPORT_DIR_ENV_VAR, str(tmp_path / "reports"))

    result = vendor_network_sync.run()

    assert result["skipped"] is False
    assert result["network_calls"] is True
    assert result["source_count"] == 2
    assert result["failed_count"] == 0
    assert result["blocked_count"] == 0
    assert result["report_dir"] == str(tmp_path / "reports")
    assert [call["source_id"] for call in calls] == ["source-1", "source/2"]
    assert [call["auth_secret_env"] for call in calls] == [
        "CIVICCLERK_VENDOR_SECRET_SOURCE_1",
        "CIVICCLERK_VENDOR_SECRET_SOURCE_2",
    ]
    assert [call["output_path"] for call in calls] == [
        tmp_path / "reports" / "source-1.json",
        tmp_path / "reports" / "source_2.json",
    ]
