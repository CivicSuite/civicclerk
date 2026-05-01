"""Normalize local connector export payloads into a repeatable import ledger."""

from __future__ import annotations

import argparse
from pathlib import Path

from civicclerk.connector_import_sync import ImportAttempt, run_import_sync
from civicclerk.connectors import SUPPORTED_CONNECTORS


def _print_report(attempts: list[ImportAttempt], output_path: Path | None) -> int:
    imported_count = sum(1 for attempt in attempts if attempt.ok)
    failed_count = len(attempts) - imported_count
    print("CivicClerk connector import sync")
    print("network_calls=false")
    print(f"imported_count={imported_count}")
    print(f"failed_count={failed_count}")
    if output_path:
        print(f"ledger={output_path}")
    for attempt in attempts:
        status = "PASS" if attempt.ok else "FAIL"
        print(f"[{status}] {attempt.connector} {attempt.payload_path}: {attempt.message}")
        print(f"  fix: {attempt.fix}")
    print("CONNECTOR-IMPORT-SYNC: PASSED" if failed_count == 0 else "CONNECTOR-IMPORT-SYNC: FAILED")
    return 0 if failed_count == 0 else 1


def _print_plan(connectors: list[str], payload_dir: Path, output_path: Path | None) -> None:
    print("CivicClerk connector import sync")
    print("Network calls: disabled")
    print("Connectors: " + ", ".join(connectors))
    print(f"Payload source: {payload_dir}")
    print(f"Ledger: {output_path if output_path else 'stdout report only'}")
    print("Steps:")
    print("  1. Read local exported JSON files from <payload-dir>/<connector>.json or <payload-dir>/<connector>/*.json.")
    print("  2. Normalize each payload through the existing CivicClerk connector import contract.")
    print("  3. Write an import ledger with source provenance, normalized meeting ids, and actionable failures.")
    print("Not scheduled live sync: this runner processes local exports and does not contact vendors.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local connector import sync without outbound network calls.")
    parser.add_argument("--payload-dir", required=True, help="Directory containing connector JSON exports.")
    parser.add_argument(
        "--connector",
        action="append",
        choices=sorted(SUPPORTED_CONNECTORS),
        help="Connector to import. Repeat for multiple connectors. Defaults to all supported connectors.",
    )
    parser.add_argument("--output", help="Optional JSON ledger path for normalized import attempts.")
    parser.add_argument("--print-only", action="store_true", help="Print the import sync plan without reading payloads.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    connectors = args.connector or sorted(SUPPORTED_CONNECTORS)
    payload_dir = Path(args.payload_dir)
    output_path = Path(args.output) if args.output else None
    if args.print_only:
        _print_plan(connectors, payload_dir, output_path)
        return 0
    attempts = run_import_sync(payload_dir=payload_dir, connectors=connectors, output_path=output_path)
    return _print_report(attempts, output_path)


if __name__ == "__main__":
    raise SystemExit(main())
