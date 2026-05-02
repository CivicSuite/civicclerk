"""Vendor-network live sync readiness and health-state primitives."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import parse_qs, urlparse

from civicclerk.connectors import SUPPORTED_CONNECTORS, validate_url_host

HealthStatus = Literal["healthy", "degraded", "circuit_open"]
AuthMethod = Literal["api_key", "bearer_token", "oauth_client_credentials", "none"]

CIRCUIT_OPEN_THRESHOLD = 5
GRACE_PERIOD_CIRCUIT_OPEN_THRESHOLD = 2
SUPPORTED_LIVE_SYNC_AUTH_METHODS: set[str] = {
    "api_key",
    "bearer_token",
    "oauth_client_credentials",
    "none",
}
_SECRET_QUERY_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "token",
    "bearer",
    "client_secret",
    "password",
}


@dataclass(frozen=True)
class LiveSyncCheck:
    status: Literal["PASS", "FAIL"]
    name: str
    message: str
    fix: str


@dataclass(frozen=True)
class VendorLiveSyncConfig:
    connector: str
    source_url: str
    auth_method: AuthMethod


@dataclass(frozen=True)
class VendorSyncState:
    connector: str
    source_name: str = "vendor source"
    consecutive_failure_count: int = 0
    active_failure_count: int = 0
    sync_paused: bool = False
    sync_paused_at: datetime | None = None
    sync_paused_reason: str | None = None
    last_sync_status: str | None = None
    last_error_at: datetime | None = None

    @property
    def health_status(self) -> HealthStatus:
        return compute_health_status(self)


@dataclass(frozen=True)
class VendorSyncRunResult:
    records_discovered: int
    records_succeeded: int
    records_failed: int
    retries_attempted: int = 0
    error_summary: str | None = None

    @property
    def attempted_count(self) -> int:
        return self.records_discovered + self.retries_attempted

    @property
    def any_success(self) -> bool:
        return self.records_succeeded > 0

    @property
    def any_failure(self) -> bool:
        return self.records_failed > 0


def validate_live_sync_config(config: VendorLiveSyncConfig) -> list[LiveSyncCheck]:
    """Validate a proposed live vendor sync source without contacting it."""

    checks: list[LiveSyncCheck] = []
    connector = config.connector.strip().lower()
    supported = set(SUPPORTED_CONNECTORS)
    if connector in supported:
        checks.append(
            LiveSyncCheck(
                status="PASS",
                name="supported connector",
                message=f"{connector} is supported for the live-sync foundation.",
                fix="Keep the connector on the supported allowlist before enabling scheduled pulls.",
            )
        )
    else:
        checks.append(
            LiveSyncCheck(
                status="FAIL",
                name="supported connector",
                message=f"Unsupported connector '{config.connector}'.",
                fix="Use one of: " + ", ".join(sorted(supported)) + ".",
            )
        )

    try:
        validate_url_host(config.source_url)
    except ValueError as exc:
        checks.append(
            LiveSyncCheck(
                status="FAIL",
                name="source URL",
                message=str(exc),
                fix="Use a resolvable vendor HTTPS host outside loopback, link-local, and private blocked ranges.",
            )
        )
    else:
        checks.append(
            LiveSyncCheck(
                status="PASS",
                name="source URL",
                message="source URL host passed shared CivicCore validation.",
                fix="Store credentials in deployment secrets; do not put them in the URL.",
            )
        )

    checks.append(_credential_location_check(config.source_url))

    if config.auth_method in SUPPORTED_LIVE_SYNC_AUTH_METHODS:
        checks.append(
            LiveSyncCheck(
                status="PASS",
                name="auth method",
                message=f"{config.auth_method} is an allowed live-sync auth method.",
                fix="Configure the secret value through the deployment secret store before live pulls are enabled.",
            )
        )
    else:
        checks.append(
            LiveSyncCheck(
                status="FAIL",
                name="auth method",
                message=f"Unsupported auth method '{config.auth_method}'.",
                fix="Use one of: " + ", ".join(sorted(SUPPORTED_LIVE_SYNC_AUTH_METHODS)) + ".",
            )
        )

    return checks


def live_sync_config_ready(checks: list[LiveSyncCheck]) -> bool:
    return all(check.status == "PASS" for check in checks)


def apply_vendor_sync_result(
    state: VendorSyncState,
    result: VendorSyncRunResult,
    *,
    now: datetime | None = None,
) -> VendorSyncState:
    """Apply one run result using the CivicRecords AI circuit-breaker pattern."""

    now = now or datetime.now(UTC)
    if result.attempted_count == 0 and not result.any_failure:
        return replace(state, last_sync_status="success")

    if result.any_success:
        return replace(
            state,
            consecutive_failure_count=0,
            sync_paused=False,
            sync_paused_at=None,
            sync_paused_reason=None if state.sync_paused_reason == "grace_period" else state.sync_paused_reason,
            last_sync_status="partial" if result.any_failure else "success",
        )

    if result.any_failure:
        failure_count = state.consecutive_failure_count + 1
        threshold = (
            GRACE_PERIOD_CIRCUIT_OPEN_THRESHOLD
            if state.sync_paused_reason == "grace_period"
            else CIRCUIT_OPEN_THRESHOLD
        )
        if failure_count >= threshold:
            return replace(
                state,
                consecutive_failure_count=failure_count,
                sync_paused=True,
                sync_paused_at=now,
                sync_paused_reason=f"Circuit open after {failure_count} consecutive full-run failures.",
                last_sync_status="failed",
                last_error_at=now,
            )
        return replace(
            state,
            consecutive_failure_count=failure_count,
            last_sync_status="failed",
            last_error_at=now,
        )

    return replace(state, last_sync_status="success")


def compute_health_status(state: VendorSyncState) -> HealthStatus:
    if state.sync_paused:
        return "circuit_open"
    if state.consecutive_failure_count > 0 or state.active_failure_count > 0:
        return "degraded"
    return "healthy"


def operator_status(state: VendorSyncState) -> dict[str, str | int | bool | None]:
    health = compute_health_status(state)
    if health == "circuit_open":
        message = f"{state.source_name} live sync is paused because the circuit breaker is open."
        fix = (
            "Review the latest run errors, correct the vendor credentials or endpoint, "
            "run a one-time readiness check, then unpause the source."
        )
    elif health == "degraded":
        message = f"{state.source_name} live sync is degraded."
        fix = (
            "Review active failures and confirm the next scheduled sync can reach the vendor endpoint; "
            "the circuit opens after five consecutive full-run failures."
        )
    else:
        message = f"{state.source_name} live sync is healthy."
        fix = "No action needed. Continue monitoring scheduled run logs."
    return {
        "connector": state.connector,
        "source_name": state.source_name,
        "health_status": health,
        "consecutive_failure_count": state.consecutive_failure_count,
        "active_failure_count": state.active_failure_count,
        "sync_paused": state.sync_paused,
        "sync_paused_reason": state.sync_paused_reason,
        "message": message,
        "fix": fix,
    }


def _credential_location_check(source_url: str) -> LiveSyncCheck:
    parsed = urlparse(source_url)
    query_keys = {key.lower() for key in parse_qs(parsed.query)}
    if parsed.username or parsed.password or query_keys.intersection(_SECRET_QUERY_KEYS):
        return LiveSyncCheck(
            status="FAIL",
            name="credential location",
            message="source URL appears to include credentials or token query parameters.",
            fix="Remove credentials from the URL and configure them through deployment secrets.",
        )
    return LiveSyncCheck(
        status="PASS",
        name="credential location",
        message="source URL does not expose credentials in userinfo or known token query parameters.",
        fix="Keep API keys, bearer tokens, and client secrets out of URLs and checked-in docs.",
    )
