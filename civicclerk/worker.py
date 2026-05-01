from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from celery import Celery

from civicclerk.connector_import_sync import attempt_dict, run_import_sync
from civicclerk.connectors import SUPPORTED_CONNECTORS

CONNECTOR_SYNC_ENABLED_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_ENABLED"
CONNECTOR_SYNC_PAYLOAD_DIR_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_PAYLOAD_DIR"
CONNECTOR_SYNC_LEDGER_PATH_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_LEDGER_PATH"
CONNECTOR_SYNC_CONNECTORS_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_CONNECTORS"
CONNECTOR_SYNC_INTERVAL_SECONDS_ENV_VAR = "CIVICCLERK_CONNECTOR_SYNC_INTERVAL_SECONDS"
DEFAULT_CONNECTOR_SYNC_PAYLOAD_DIR = "/data/connector-imports"
DEFAULT_CONNECTOR_SYNC_LEDGER_PATH = "/data/exports/connector-import-ledger.json"
DEFAULT_CONNECTOR_SYNC_INTERVAL_SECONDS = 900


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

    if os.environ.get(CONNECTOR_SYNC_ENABLED_ENV_VAR, "").strip().lower() not in {"1", "true", "yes", "on"}:
        return {
            "skipped": True,
            "message": "Scheduled connector import sync is disabled.",
            "fix": f"Set {CONNECTOR_SYNC_ENABLED_ENV_VAR}=true after configuring the local export drop folder.",
        }

    payload_dir = Path(os.environ.get(CONNECTOR_SYNC_PAYLOAD_DIR_ENV_VAR, DEFAULT_CONNECTOR_SYNC_PAYLOAD_DIR))
    ledger_path = Path(os.environ.get(CONNECTOR_SYNC_LEDGER_PATH_ENV_VAR, DEFAULT_CONNECTOR_SYNC_LEDGER_PATH))
    connectors = _connector_sync_connectors()
    attempts = run_import_sync(payload_dir=payload_dir, connectors=connectors, output_path=ledger_path)
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


def _connector_sync_interval_seconds() -> int:
    raw = os.environ.get(CONNECTOR_SYNC_INTERVAL_SECONDS_ENV_VAR, "").strip()
    if not raw:
        return DEFAULT_CONNECTOR_SYNC_INTERVAL_SECONDS
    try:
        interval = int(raw)
    except ValueError:
        return DEFAULT_CONNECTOR_SYNC_INTERVAL_SECONDS
    return max(interval, 60)


def _connector_sync_connectors() -> list[str]:
    raw = os.environ.get(CONNECTOR_SYNC_CONNECTORS_ENV_VAR, "").strip()
    if not raw:
        return sorted(SUPPORTED_CONNECTORS)
    requested = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return requested or sorted(SUPPORTED_CONNECTORS)


if os.environ.get(CONNECTOR_SYNC_ENABLED_ENV_VAR, "").strip().lower() in {"1", "true", "yes", "on"}:
    app.conf.beat_schedule = {
        "civicclerk-scheduled-connector-import-sync": {
            "task": "civicclerk.connector_import_sync",
            "schedule": _connector_sync_interval_seconds(),
        }
    }
