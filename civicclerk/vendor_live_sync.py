"""Vendor-network live sync readiness and CivicCore-backed health primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.parse import parse_qs, urlparse

from civiccore.connectors import (
    SyncCircuitPolicy,
    SyncCircuitState,
    SyncHealthStatus,
    SyncRunResult,
    apply_sync_run_result,
    build_sync_operator_status,
    compute_sync_health_status,
)

from civicclerk.connectors import SUPPORTED_CONNECTORS, validate_url_host

AuthMethod = Literal["api_key", "bearer_token", "oauth_client_credentials", "none"]

CIRCUIT_OPEN_THRESHOLD = 5
GRACE_PERIOD_CIRCUIT_OPEN_THRESHOLD = 2
_CIVICCLERK_CIRCUIT_POLICY = SyncCircuitPolicy(
    full_failure_threshold=CIRCUIT_OPEN_THRESHOLD,
    grace_period_failure_threshold=GRACE_PERIOD_CIRCUIT_OPEN_THRESHOLD,
)
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


VendorSyncState = SyncCircuitState
VendorSyncRunResult = SyncRunResult


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
    """Apply one run result using the shared CivicCore circuit-breaker pattern."""

    return apply_sync_run_result(
        state,
        result,
        now=now,
        policy=_CIVICCLERK_CIRCUIT_POLICY,
    )


def compute_health_status(state: VendorSyncState) -> SyncHealthStatus:
    return compute_sync_health_status(state)


def operator_status(state: VendorSyncState) -> dict[str, str | int | bool | None]:
    return build_sync_operator_status(state, policy=_CIVICCLERK_CIRCUIT_POLICY).public_dict()


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
