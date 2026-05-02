"""Opt-in vendor-network live sync runner.

The runner is intentionally narrow: it fetches JSON from an already-approved
vendor source, normalizes each payload through the existing connector contract,
and records the run outcome in the vendor sync ledger.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from civicclerk.connectors import ConnectorImportError, import_meeting_payload, validate_url_host
from civicclerk.vendor_live_sync import VendorSyncRunResult
from civicclerk.vendor_delta import plan_vendor_delta_request
from civicclerk.vendor_sync_persistence import VendorSyncRepository, VendorSyncSourceRecord

NETWORK_ENABLED_ENV_VAR = "CIVICCLERK_VENDOR_NETWORK_SYNC_ENABLED"
DEFAULT_TIMEOUT_SECONDS = 20
FetchJson = Callable[[VendorSyncSourceRecord, dict[str, str], int], Any]


@dataclass(frozen=True)
class VendorNetworkSyncAttempt:
    ok: bool
    message: str
    fix: str
    external_meeting_id: str | None = None
    error_class: str | None = None


@dataclass(frozen=True)
class VendorNetworkSyncReport:
    source_id: str
    connector: str
    network_calls: bool
    records_discovered: int
    records_succeeded: int
    records_failed: int
    run_status: str | None
    source_health_status: str | None
    delta_request_url: str | None
    cursor_param: str | None
    cursor_value: str | None
    cursor_advanced_at: str | None
    message: str
    fix: str
    attempts: list[VendorNetworkSyncAttempt]

    def public_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "connector": self.connector,
            "network_calls": self.network_calls,
            "records_discovered": self.records_discovered,
            "records_succeeded": self.records_succeeded,
            "records_failed": self.records_failed,
            "run_status": self.run_status,
            "source_health_status": self.source_health_status,
            "delta_request_url": self.delta_request_url,
            "cursor_param": self.cursor_param,
            "cursor_value": self.cursor_value,
            "cursor_advanced_at": self.cursor_advanced_at,
            "message": self.message,
            "fix": self.fix,
            "attempts": [attempt.__dict__ for attempt in self.attempts],
        }


def run_vendor_network_sync(
    *,
    repository: VendorSyncRepository,
    source_id: str,
    enable_network: bool = False,
    auth_secret: str | None = None,
    auth_secret_env: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    fetch_json: FetchJson | None = None,
    output_path: Path | None = None,
) -> VendorNetworkSyncReport:
    """Run one explicit vendor-network pull and persist its health outcome."""

    source = repository.get_source(source_id)
    if source is None:
        return _finalize_report(
            output_path=output_path,
            report=_blocked_report(
                source_id=source_id,
                connector="unknown",
                message="Vendor live-sync source was not found.",
                fix="Create and validate the source with POST /vendor-live-sync/sources before running a vendor pull.",
            ),
        )
    if source.sync_paused:
        return _finalize_report(
            output_path=output_path,
            report=_blocked_report(
                source_id=source.id,
                connector=source.connector,
                message="Vendor live sync is paused because the circuit breaker is open.",
                fix="Review the run log, correct the vendor endpoint or credentials, then unpause the source before retrying.",
                source_health_status=source.public_dict()["health_status"],
            ),
        )
    if not enable_network and os.environ.get(NETWORK_ENABLED_ENV_VAR, "").lower() != "true":
        return _finalize_report(
            output_path=output_path,
            report=_blocked_report(
                source_id=source.id,
                connector=source.connector,
                message="Vendor-network sync is disabled.",
                fix=f"Set {NETWORK_ENABLED_ENV_VAR}=true or pass --enable-network for this one-time pull.",
                source_health_status=source.public_dict()["health_status"],
            ),
        )

    try:
        validate_url_host(source.source_url)
        delta_plan = plan_vendor_delta_request(
            connector=source.connector,
            source_url=source.source_url,
            changed_since=source.last_success_cursor_at,
        )
        request_source = replace(source, source_url=delta_plan.request_url)
        secret = _resolve_auth_secret(source=source, auth_secret=auth_secret, auth_secret_env=auth_secret_env)
        headers = _auth_headers(source=source, secret=secret)
        cursor_advance_at = datetime.now(UTC)
        raw_payloads = _coerce_payloads((fetch_json or _fetch_json)(request_source, headers, timeout_seconds))
    except VendorNetworkSyncError as exc:
        return _finalize_report(
            output_path=output_path,
            report=_record_failed_run(
                repository=repository,
                source=source,
                message=exc.message,
                fix=exc.fix,
                network_attempted=exc.network_attempted,
            ),
        )
    except ValueError as exc:
        return _finalize_report(
            output_path=output_path,
            report=_record_failed_run(
                repository=repository,
                source=source,
                message=str(exc),
                fix="Re-run source readiness, verify the host is still allowed, and save the corrected source before retrying.",
                network_attempted=False,
            ),
        )

    attempts = [_normalize_payload(source.connector, payload) for payload in raw_payloads]
    records_succeeded = sum(1 for attempt in attempts if attempt.ok)
    records_failed = len(attempts) - records_succeeded
    error_summary = "; ".join(attempt.message for attempt in attempts if not attempt.ok) or None
    recorded = repository.record_run(
        source_id=source.id,
        result=VendorSyncRunResult(
            records_discovered=len(raw_payloads),
            records_succeeded=records_succeeded,
            records_failed=records_failed,
            error_summary=error_summary,
        ),
        advance_success_cursor=records_failed == 0,
        cursor_at=cursor_advance_at,
    )
    if recorded is None:
        return _finalize_report(
            output_path=output_path,
            report=_blocked_report(
                source_id=source.id,
                connector=source.connector,
                message="Vendor sync run could not be recorded.",
                fix="Confirm CIVICCLERK_VENDOR_SYNC_DB_URL points at the live vendor sync ledger and retry.",
            ),
        )
    updated_source, run = recorded
    if records_failed:
        message = error_summary or "Vendor-network sync finished with failed records."
        fix = "Fix the failed payloads or connector mapping, then rerun before enabling scheduled pulls."
    else:
        message = "Vendor-network sync completed and the run outcome was recorded."
        fix = updated_source.public_dict()["fix"]
    report = VendorNetworkSyncReport(
        source_id=source.id,
        connector=source.connector,
        network_calls=True,
        records_discovered=len(raw_payloads),
        records_succeeded=records_succeeded,
        records_failed=records_failed,
        run_status=run.status,
        source_health_status=updated_source.public_dict()["health_status"],
        delta_request_url=delta_plan.request_url,
        cursor_param=delta_plan.cursor_param,
        cursor_value=delta_plan.cursor_value,
        cursor_advanced_at=updated_source.public_dict()["last_success_cursor_at"],
        message=message,
        fix=fix,
        attempts=attempts,
    )
    return _finalize_report(report=report, output_path=output_path)


class VendorNetworkSyncError(RuntimeError):
    def __init__(self, *, message: str, fix: str, network_attempted: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.fix = fix
        self.network_attempted = network_attempted


def _resolve_auth_secret(
    *,
    source: VendorSyncSourceRecord,
    auth_secret: str | None,
    auth_secret_env: str | None,
) -> str | None:
    if source.auth_method == "none":
        return None
    secret = auth_secret or (os.environ.get(auth_secret_env) if auth_secret_env else None)
    if not secret:
        raise VendorNetworkSyncError(
            message=f"{source.auth_method} credentials are required before contacting the vendor.",
            fix="Pass --auth-secret-env with a populated deployment secret; do not put credentials in the source URL.",
        )
    return secret


def _auth_headers(*, source: VendorSyncSourceRecord, secret: str | None) -> dict[str, str]:
    if source.auth_method == "bearer_token":
        return {"Authorization": f"Bearer {secret}"}
    if source.auth_method == "api_key":
        return {"X-API-Key": secret or ""}
    if source.auth_method == "oauth_client_credentials":
        return {"Authorization": f"Bearer {secret}"}
    return {}


def _fetch_json(source: VendorSyncSourceRecord, headers: dict[str, str], timeout_seconds: int) -> Any:
    request = Request(source.source_url, headers={"Accept": "application/json", **headers})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - URL validated by CivicCore guard.
            content_type = response.headers.get("content-type", "")
            body = response.read()
    except URLError as exc:
        raise VendorNetworkSyncError(
            message=f"Vendor endpoint could not be reached: {exc.reason}.",
            fix="Confirm the vendor URL, firewall route, and credentials, then retry. The circuit breaker will pause after repeated full-run failures.",
            network_attempted=True,
        ) from exc
    if "json" not in content_type.lower():
        raise VendorNetworkSyncError(
            message=f"Vendor endpoint returned non-JSON content type: {content_type or 'missing content-type'}.",
            fix="Use a vendor API endpoint that returns the supported meeting JSON payload.",
            network_attempted=True,
        )
    try:
        return json.loads(body.decode("utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise VendorNetworkSyncError(
            message=f"Vendor endpoint returned invalid JSON: {exc.msg}.",
            fix="Confirm the vendor API response body is valid JSON before enabling scheduled pulls.",
            network_attempted=True,
        ) from exc


def _coerce_payloads(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        payloads = payload
    else:
        payloads = [payload]
    if not all(isinstance(item, dict) for item in payloads):
        raise VendorNetworkSyncError(
            message="Vendor response must be a JSON object or a list of JSON objects.",
            fix="Point the source URL at a meeting payload endpoint or add a connector-specific response adapter.",
        )
    return payloads


def _normalize_payload(connector: str, payload: dict[str, Any]) -> VendorNetworkSyncAttempt:
    try:
        imported = import_meeting_payload(connector_name=connector, payload=payload)
    except ConnectorImportError as exc:
        public = exc.public_dict()
        return VendorNetworkSyncAttempt(
            ok=False,
            message=public["message"],
            fix=public["fix"],
            error_class=exc.__class__.__name__,
        )
    normalized = imported.public_dict()
    return VendorNetworkSyncAttempt(
        ok=True,
        message=f"normalized meeting {normalized['external_meeting_id']}.",
        fix="Review source provenance before promoting imported items into clerk workflows.",
        external_meeting_id=normalized["external_meeting_id"],
    )


def _record_failed_run(
    *,
    repository: VendorSyncRepository,
    source: VendorSyncSourceRecord,
    message: str,
    fix: str,
    network_attempted: bool,
) -> VendorNetworkSyncReport:
    recorded = repository.record_run(
        source_id=source.id,
        result=VendorSyncRunResult(
            records_discovered=1,
            records_succeeded=0,
            records_failed=1,
            error_summary=message,
        ),
    )
    updated_source = recorded[0] if recorded else source
    return VendorNetworkSyncReport(
        source_id=source.id,
        connector=source.connector,
        network_calls=network_attempted,
        records_discovered=1,
        records_succeeded=0,
        records_failed=1,
        run_status=recorded[1].status if recorded else "failed",
        source_health_status=updated_source.public_dict()["health_status"],
        delta_request_url=None,
        cursor_param=None,
        cursor_value=None,
        cursor_advanced_at=updated_source.public_dict()["last_success_cursor_at"],
        message=message,
        fix=fix,
        attempts=[
            VendorNetworkSyncAttempt(
                ok=False,
                message=message,
                fix=fix,
                error_class="VendorNetworkSyncError",
            )
        ],
    )


def _blocked_report(
    *,
    source_id: str,
    connector: str,
    message: str,
    fix: str,
    source_health_status: str | None = None,
) -> VendorNetworkSyncReport:
    return VendorNetworkSyncReport(
        source_id=source_id,
        connector=connector,
        network_calls=False,
        records_discovered=0,
        records_succeeded=0,
        records_failed=0,
        run_status=None,
        source_health_status=source_health_status,
        delta_request_url=None,
        cursor_param=None,
        cursor_value=None,
        cursor_advanced_at=None,
        message=message,
        fix=fix,
        attempts=[],
    )


def _write_report(report: VendorNetworkSyncReport, output_path: Path | None) -> None:
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.public_dict(), indent=2) + "\n", encoding="utf-8")


def _finalize_report(*, report: VendorNetworkSyncReport, output_path: Path | None) -> VendorNetworkSyncReport:
    _write_report(report, output_path)
    return report
