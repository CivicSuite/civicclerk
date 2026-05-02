"""Check CivicClerk vendor live-sync configuration without vendor network calls."""

from __future__ import annotations

import argparse

from civicclerk.connectors import SUPPORTED_CONNECTORS
from civicclerk.vendor_live_sync import (
    CIRCUIT_OPEN_THRESHOLD,
    GRACE_PERIOD_CIRCUIT_OPEN_THRESHOLD,
    SUPPORTED_LIVE_SYNC_AUTH_METHODS,
    VendorLiveSyncConfig,
    VendorSyncRunResult,
    VendorSyncState,
    apply_vendor_sync_result,
    live_sync_config_ready,
    operator_status,
    validate_live_sync_config,
)


def _print_plan() -> None:
    print("CivicClerk vendor live-sync readiness")
    print("Network calls: disabled")
    print("Purpose: validate the live-sync source contract before scheduled vendor pulls are enabled.")
    print("Circuit breaker:")
    print(f"  - opens after {CIRCUIT_OPEN_THRESHOLD} consecutive full-run failures")
    print(f"  - opens after {GRACE_PERIOD_CIRCUIT_OPEN_THRESHOLD} failures during post-unpause grace period")
    print("Health statuses: healthy, degraded, circuit_open")
    print("Fix path: validate source URL and auth method, store secrets outside URLs, then wire the vendor adapter.")
    print("Not a vendor pull: this helper does not contact Granicus, Legistar, PrimeGov, or NovusAGENDA.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check vendor live-sync readiness without outbound network calls.")
    parser.add_argument("--connector", default="legistar", choices=sorted(SUPPORTED_CONNECTORS))
    parser.add_argument("--source-url", default="https://vendor.example.gov/api/meetings")
    parser.add_argument("--auth-method", default="bearer_token", choices=sorted(SUPPORTED_LIVE_SYNC_AUTH_METHODS))
    parser.add_argument(
        "--simulate-consecutive-failures",
        type=int,
        default=0,
        help="Simulate failed full-run attempts so operators can preview degraded/circuit-open status.",
    )
    parser.add_argument(
        "--grace-period",
        action="store_true",
        help="Simulate the stricter post-unpause circuit-breaker threshold.",
    )
    parser.add_argument("--print-only", action="store_true", help="Print the readiness plan without checking inputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.print_only:
        _print_plan()
        return 0

    checks = validate_live_sync_config(
        VendorLiveSyncConfig(
            connector=args.connector,
            source_url=args.source_url,
            auth_method=args.auth_method,
        )
    )
    state = VendorSyncState(
        connector=args.connector,
        source_name=args.connector,
        sync_paused_reason="grace_period" if args.grace_period else None,
    )
    for _ in range(max(args.simulate_consecutive_failures, 0)):
        state = apply_vendor_sync_result(
            state,
            VendorSyncRunResult(records_discovered=1, records_succeeded=0, records_failed=1),
        )

    status = operator_status(state)
    ready = live_sync_config_ready(checks)

    print("CivicClerk vendor live-sync readiness")
    print(f"live_sync_ready={str(ready).lower()}")
    print("network_calls=false")
    print(f"health_status={status['health_status']}")
    print(f"consecutive_failure_count={status['consecutive_failure_count']}")
    print(f"sync_paused={str(status['sync_paused']).lower()}")
    print(f"operator_message={status['message']}")
    print(f"operator_fix={status['fix']}")
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.message}")
        print(f"  fix: {check.fix}")
    print("VENDOR-LIVE-SYNC-READINESS: PASSED" if ready else "VENDOR-LIVE-SYNC-READINESS: FAILED")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
