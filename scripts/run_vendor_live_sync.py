"""Run one explicit vendor-network live sync source."""

from __future__ import annotations

import argparse
from pathlib import Path

from civicclerk.vendor_network_sync import NETWORK_ENABLED_ENV_VAR, run_vendor_network_sync
from civicclerk.vendor_sync_persistence import VendorSyncRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one approved vendor-network live sync source.")
    parser.add_argument("--source-id", required=True, help="Vendor sync source id from /vendor-live-sync/sources.")
    parser.add_argument("--db-url", help="Vendor sync ledger URL. Defaults to CIVICCLERK_VENDOR_SYNC_DB_URL.")
    parser.add_argument(
        "--auth-secret-env",
        help="Name of the environment variable containing the source credential.",
    )
    parser.add_argument(
        "--enable-network",
        action="store_true",
        help=f"Allow this one-time vendor pull. Otherwise {NETWORK_ENABLED_ENV_VAR}=true is required.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--output", help="Optional JSON report path.")
    parser.add_argument("--print-only", action="store_true", help="Print the guarded run plan without contacting vendors.")
    return parser.parse_args()


def _print_plan(args: argparse.Namespace) -> None:
    print("CivicClerk vendor-network live sync")
    print(f"Source id: {args.source_id}")
    print("Network calls: disabled in print-only mode")
    print(f"Network gate: pass --enable-network or set {NETWORK_ENABLED_ENV_VAR}=true")
    print("Steps:")
    print("  1. Load the approved source from the vendor sync ledger.")
    print("  2. Refuse to run if the source circuit is open.")
    print("  3. Re-validate the source URL before any HTTP request.")
    print("  4. Read credentials from --auth-secret-env, never from the source URL.")
    print("  5. Fetch JSON, normalize it through the existing connector contract, and record the run outcome.")


def main() -> int:
    args = parse_args()
    if args.print_only:
        _print_plan(args)
        return 0

    repository = VendorSyncRepository(db_url=args.db_url)
    report = run_vendor_network_sync(
        repository=repository,
        source_id=args.source_id,
        enable_network=args.enable_network,
        auth_secret_env=args.auth_secret_env,
        timeout_seconds=args.timeout_seconds,
        output_path=Path(args.output) if args.output else None,
    )
    print("CivicClerk vendor-network live sync")
    print(f"network_calls={str(report.network_calls).lower()}")
    print(f"records_discovered={report.records_discovered}")
    print(f"records_succeeded={report.records_succeeded}")
    print(f"records_failed={report.records_failed}")
    print(f"run_status={report.run_status or 'not_run'}")
    print(f"source_health_status={report.source_health_status or 'unknown'}")
    print(f"message={report.message}")
    print(f"fix={report.fix}")
    if args.output:
        print(f"report={args.output}")
    print("VENDOR-NETWORK-SYNC: PASSED" if report.records_failed == 0 else "VENDOR-NETWORK-SYNC: FAILED")
    return 0 if report.records_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

