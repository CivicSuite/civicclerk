from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from celery import Celery

from civicclerk.connector_import_sync import attempt_dict, run_import_sync
from civicclerk.connectors import SUPPORTED_CONNECTORS
from civicclerk.vendor_network_sync import (
    NETWORK_ENABLED_ENV_VAR,
    run_vendor_network_sync,
)
from civicclerk.vendor_sync_persistence import VendorSyncRepository

CONNECTOR_SYNC_ENABLED_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_ENABLED"
CONNECTOR_SYNC_PAYLOAD_DIR_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_PAYLOAD_DIR"
CONNECTOR_SYNC_LEDGER_PATH_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_LEDGER_PATH"
CONNECTOR_SYNC_CONNECTORS_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_CONNECTORS"
CONNECTOR_SYNC_INTERVAL_SECONDS_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_INTERVAL_SECONDS"
VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR = (
    "CIVICCLERK_VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED"
)
VENDOR_NETWORK_SYNC_SOURCE_IDS_ENV_VAR = "CIVICCLERK_VENDOR_NETWORK_SYNC_SOURCE_IDS"
VENDOR_NETWORK_SYNC_DB_URL_ENV_VAR = "CIVICCLERK_VENDOR_SYNC_DB_URL"
VENDOR_NETWORK_SYNC_AUTH_SECRET_ENV_VAR = (
    "CIVICCLERK_VENDOR_NETWORK_SYNC_AUTH_SECRET_ENV"
)
VENDOR_NETWORK_SYNC_AUTH_SECRET_ENV_PREFIX_ENV_VAR = (
    "CIVICCLERK_VENDOR_NETWORK_SYNC_AUTH_SECRET_ENV_PREFIX"
)
VENDOR_NETWORK_SYNC_REPORT_DIR_ENV_VAR = "CIVICCLERK_VENDOR_NETWORK_SYNC_REPORT_DIR"
VENDOR_NETWORK_SYNC_INTERVAL_SECONDS_ENV_VAR = (
    "CIVICCLERK_VENDOR_NETWORK_SYNC_INTERVAL_SECONDS"
)
DEFAULT_CONNECTOR_SYNC_PAYLOAD_DIR = "/data/connector-imports"
DEFAULT_CONNECTOR_SYNC_LEDGER_PATH = "/data/exports/connector-import-ledger.json"
DEFAULT_CONNECTOR_SYNC_INTERVAL_SECONDS = 900
DEFAULT_VENDOR_NETWORK_SYNC_REPORT_DIR = "/data/exports/vendor-network-sync"
DEFAULT_VENDOR_NETWORK_SYNC_AUTH_SECRET_ENV_PREFIX = "CIVICCLERK_VENDOR_SECRET_"
DEFAULT_VENDOR_NETWORK_SYNC_INTERVAL_SECONDS = 900


def _redis_url() -> str:
    return os.environ.get("CIVICCLERK_REDIS_URL", "redis://redis:6379/0")


app = Celery("civicclerk", broker=_redis_url(), backend=_redis_url())
app.conf.update(
    task_default_queue="civicclerk",
    timezone="UTC",
)


@app.task(name="civicclerk.healthcheck")
def healthcheck() -> str:
    return "ok"


@app.task(name="civicclerk.connector_import_sync")
def connector_import_sync() -> dict[str, Any]:
    """Normalize approved local connector export drops on a Beat schedule."""

    if os.environ.get(CONNECTOR_SYNC_ENABLED_ENV_VAR, "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return {
            "skipped": True,
            "message": "Scheduled connector import sync is disabled.",
            "fix": f"Set {CONNECTOR_SYNC_ENABLED_ENV_VAR}=true after configuring the local export drop folder.",
        }

    payload_dir = Path(
        os.environ.get(
            CONNECTOR_SYNC_PAYLOAD_DIR_ENV_VAR, DEFAULT_CONNECTOR_SYNC_PAYLOAD_DIR
        )
    )
    ledger_path = Path(
        os.environ.get(
            CONNECTOR_SYNC_LEDGER_PATH_ENV_VAR, DEFAULT_CONNECTOR_SYNC_LEDGER_PATH
        )
    )
    connectors = _connector_sync_connectors()
    attempts = run_import_sync(
        payload_dir=payload_dir, connectors=connectors, output_path=ledger_path
    )
    imported_count = sum(1 for attempt in attempts if attempt.ok)
    failed_count = len(attempts) - imported_count
    return {
        "skipped": False,
        "network_calls": False,
        "payload_dir": str(payload_dir),
        "ledger": str(ledger_path),
        "imported_count": imported_count,
        "failed_count": failed_count,
        "attempts": [attempt_dict(attempt) for attempt in attempts],
        "fix": (
            "Review failed attempts, export corrected local JSON from the agenda system, "
            "and leave vendor network credentials outside this local-first sync."
        )
        if failed_count
        else "Review source provenance before promoting imported items into clerk workflows.",
    }


@app.task(name="civicclerk.vendor_network_sync")
def vendor_network_sync() -> dict[str, Any]:
    """Pull approved vendor-network sources on a Beat schedule."""

    if not _env_enabled(VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR):
        return {
            "skipped": True,
            "network_calls": False,
            "message": "Scheduled vendor-network sync is disabled.",
            "fix": (
                f"Set {VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR}=true only after source readiness, "
                f"credentials, and {NETWORK_ENABLED_ENV_VAR}=true are configured."
            ),
        }
    if not _env_enabled(NETWORK_ENABLED_ENV_VAR):
        return {
            "skipped": True,
            "network_calls": False,
            "message": "Scheduled vendor-network sync is enabled but network calls are still gated off.",
            "fix": f"Set {NETWORK_ENABLED_ENV_VAR}=true when IT is ready for scheduled vendor pulls.",
        }

    source_ids = _vendor_network_sync_source_ids()
    if not source_ids:
        return {
            "skipped": True,
            "network_calls": False,
            "message": "Scheduled vendor-network sync has no approved source IDs.",
            "fix": (
                f"Set {VENDOR_NETWORK_SYNC_SOURCE_IDS_ENV_VAR} to one or more source IDs already created "
                "through /vendor-live-sync/sources."
            ),
        }

    repository = VendorSyncRepository(
        db_url=os.environ.get(VENDOR_NETWORK_SYNC_DB_URL_ENV_VAR)
    )
    report_dir = Path(
        os.environ.get(
            VENDOR_NETWORK_SYNC_REPORT_DIR_ENV_VAR,
            DEFAULT_VENDOR_NETWORK_SYNC_REPORT_DIR,
        )
    )
    reports = []
    for source_id in source_ids:
        report = run_vendor_network_sync(
            repository=repository,
            source_id=source_id,
            auth_secret_env=_vendor_network_sync_auth_secret_env(source_id),
            output_path=report_dir / f"{_safe_report_stem(source_id)}.json",
        )
        reports.append(report.public_dict())

    failed_count = sum(1 for report in reports if report["records_failed"] > 0)
    blocked_count = sum(1 for report in reports if report["run_status"] is None)
    return {
        "skipped": False,
        "network_calls": any(report["network_calls"] for report in reports),
        "source_count": len(reports),
        "failed_count": failed_count,
        "blocked_count": blocked_count,
        "report_dir": str(report_dir),
        "reports": reports,
        "fix": (
            "Review failed or blocked source reports before leaving scheduled pulls enabled."
            if failed_count or blocked_count
            else "No action needed. Continue monitoring scheduled vendor-network run logs."
        ),
    }


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _connector_sync_interval_seconds() -> int:
    raw = os.environ.get(CONNECTOR_SYNC_INTERVAL_SECONDS_ENV_VAR, "").strip()
    if not raw:
        return DEFAULT_CONNECTOR_SYNC_INTERVAL_SECONDS
    try:
        interval = int(raw)
    except ValueError:
        return DEFAULT_CONNECTOR_SYNC_INTERVAL_SECONDS
    return max(interval, 60)


def _vendor_network_sync_interval_seconds() -> int:
    raw = os.environ.get(VENDOR_NETWORK_SYNC_INTERVAL_SECONDS_ENV_VAR, "").strip()
    if not raw:
        return DEFAULT_VENDOR_NETWORK_SYNC_INTERVAL_SECONDS
    try:
        interval = int(raw)
    except ValueError:
        return DEFAULT_VENDOR_NETWORK_SYNC_INTERVAL_SECONDS
    return max(interval, 60)


def _connector_sync_connectors() -> list[str]:
    raw = os.environ.get(CONNECTOR_SYNC_CONNECTORS_ENV_VAR, "").strip()
    if not raw:
        return sorted(SUPPORTED_CONNECTORS)
    requested = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return requested or sorted(SUPPORTED_CONNECTORS)


def _vendor_network_sync_source_ids() -> list[str]:
    raw = os.environ.get(VENDOR_NETWORK_SYNC_SOURCE_IDS_ENV_VAR, "").strip()
    return [item.strip() for item in raw.split(",") if item.strip()]


def _vendor_network_sync_auth_secret_env(source_id: str) -> str | None:
    shared_secret_env = os.environ.get(
        VENDOR_NETWORK_SYNC_AUTH_SECRET_ENV_VAR, ""
    ).strip()
    if shared_secret_env:
        return shared_secret_env
    prefix = os.environ.get(
        VENDOR_NETWORK_SYNC_AUTH_SECRET_ENV_PREFIX_ENV_VAR,
        DEFAULT_VENDOR_NETWORK_SYNC_AUTH_SECRET_ENV_PREFIX,
    ).strip()
    return f"{prefix}{_safe_secret_suffix(source_id)}" if prefix else None


def _safe_secret_suffix(source_id: str) -> str:
    return "".join(
        character if character.isalnum() else "_" for character in source_id
    ).upper()


def _safe_report_stem(source_id: str) -> str:
    safe = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in source_id
    )
    return safe or "unknown-source"


beat_schedule: dict[str, dict[str, object]] = {}
if _env_enabled(CONNECTOR_SYNC_ENABLED_ENV_VAR):
    beat_schedule.update(
        {
            "civicclerk-scheduled-connector-import-sync": {
                "task": "civicclerk.connector_import_sync",
                "schedule": _connector_sync_interval_seconds(),
            }
        }
    )
if _env_enabled(VENDOR_NETWORK_SYNC_SCHEDULE_ENABLED_ENV_VAR):
    beat_schedule.update(
        {
            "civicclerk-scheduled-vendor-network-sync": {
                "task": "civicclerk.vendor_network_sync",
                "schedule": _vendor_network_sync_interval_seconds(),
            }
        }
    )
if beat_schedule:
    app.conf.beat_schedule = beat_schedule
