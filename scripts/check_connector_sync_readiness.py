"""Check CivicClerk connector inputs for future live-sync work without networking."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from civicclerk.connectors import (
    ConnectorImportError,
    SUPPORTED_CONNECTORS,
    import_meeting_payload,
    validate_odbc_connection_string,
    validate_url_host,
)


SAMPLE_PAYLOADS: dict[str, dict] = {
    "granicus": {
        "id": "gr-100",
        "name": "Budget Hearing",
        "start": "2026-05-05T19:00:00Z",
        "agenda": [{"id": "gr-item-1", "title": "Adopt budget ordinance", "department": "Finance"}],
    },
    "legistar": {
        "MeetingId": "leg-200",
        "MeetingName": "Council Regular Meeting",
        "MeetingDate": "2026-05-06T18:30:00Z",
        "AgendaItems": [{"FileNumber": "24-001", "Title": "Approve minutes", "DepartmentName": "Clerk"}],
    },
    "primegov": {
        "meeting_id": "pg-300",
        "title": "Planning Commission",
        "scheduled_start": "2026-05-07T17:00:00Z",
        "items": [{"item_id": "pg-item-1", "subject": "Subdivision plat", "owner": "Planning"}],
    },
    "novusagenda": {
        "MeetingGuid": "na-400",
        "MeetingTitle": "Board Work Session",
        "MeetingDateTime": "2026-05-08T16:00:00Z",
        "Agenda": [{"Guid": "na-item-1", "Caption": "Capital plan update", "Dept": "Public Works"}],
    },
}


@dataclass(frozen=True)
class Check:
    status: str
    name: str
    message: str
    fix: str


def _payload_for(connector: str, payload_dir: Path | None) -> dict:
    if payload_dir is None:
        return SAMPLE_PAYLOADS[connector]
    payload_path = payload_dir / f"{connector}.json"
    if not payload_path.exists():
        raise FileNotFoundError(f"missing {payload_path}")
    return json.loads(payload_path.read_text(encoding="utf-8"))


def build_checks(
    *,
    connectors: list[str],
    payload_dir: Path | None,
    source_url: str | None,
    odbc_connection_string: str | None,
) -> list[Check]:
    checks: list[Check] = []
    supported = set(SUPPORTED_CONNECTORS)
    unknown = [connector for connector in connectors if connector not in supported]
    if unknown:
        checks.append(
            Check(
                status="FAIL",
                name="supported connectors",
                message="unsupported connector(s): " + ", ".join(unknown),
                fix="Use one of: " + ", ".join(sorted(supported)) + ".",
            )
        )
        return checks
    checks.append(
        Check(
            status="PASS",
            name="supported connectors",
            message="checking connector(s): " + ", ".join(connectors),
            fix="Keep live-sync configuration limited to the supported connector allowlist.",
        )
    )

    for connector in connectors:
        try:
            imported = import_meeting_payload(
                connector_name=connector,
                payload=_payload_for(connector, payload_dir),
            )
        except (ConnectorImportError, FileNotFoundError, json.JSONDecodeError) as exc:
            checks.append(
                Check(
                    status="FAIL",
                    name=f"{connector} local payload",
                    message=str(exc),
                    fix=f"Export a valid {connector} meeting payload as {connector}.json and retry.",
                )
            )
            continue
        checks.append(
            Check(
                status="PASS",
                name=f"{connector} local payload",
                message=(
                    f"normalized meeting {imported.external_meeting_id} with "
                    f"{len(imported.agenda_items)} agenda item(s)."
                ),
                fix="Review source provenance before promoting imported items into clerk workflows.",
            )
        )

    if source_url:
        try:
            validate_url_host(source_url)
        except ValueError as exc:
            checks.append(
                Check(
                    status="FAIL",
                    name="source URL",
                    message=str(exc),
                    fix="Use a resolvable vendor host outside loopback, link-local, and private blocked ranges.",
                )
            )
        else:
            checks.append(
                Check(
                    status="PASS",
                    name="source URL",
                    message="source URL host passed shared CivicCore validation.",
                    fix="Keep credentials out of URLs and store them in deployment secrets.",
                )
            )

    if odbc_connection_string:
        try:
            validate_odbc_connection_string(odbc_connection_string)
        except ValueError as exc:
            checks.append(
                Check(
                    status="FAIL",
                    name="ODBC connection string",
                    message=str(exc),
                    fix="Use a vendor database host outside loopback, link-local, and private blocked ranges.",
                )
            )
        else:
            checks.append(
                Check(
                    status="PASS",
                    name="ODBC connection string",
                    message="ODBC host passed shared CivicCore validation.",
                    fix="Keep passwords out of checked-in command lines and docs.",
                )
            )
    return checks


def _print_report(checks: list[Check]) -> int:
    ready = all(check.status == "PASS" for check in checks)
    print("CivicClerk connector sync readiness")
    print(f"sync_ready={str(ready).lower()}")
    print("network_calls=false")
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.message}")
        print(f"  fix: {check.fix}")
    print("CONNECTOR-SYNC-READINESS: PASSED" if ready else "CONNECTOR-SYNC-READINESS: FAILED")
    return 0 if ready else 1


def _print_plan(connectors: list[str], payload_dir: Path | None) -> None:
    print("CivicClerk connector sync readiness")
    print("Network calls: disabled")
    print("Connectors: " + ", ".join(connectors))
    print(f"Payload source: {payload_dir if payload_dir else 'built-in sample payloads'}")
    print("Steps:")
    print("  1. Confirm connector names are on the supported allowlist.")
    print("  2. Normalize each local connector payload through the shared import contract.")
    print("  3. Optionally validate future source URL or ODBC host strings with CivicCore guards.")
    print("Fix path: export local JSON payloads first; do not wire scheduled live sync until this passes.")
    print("Not live sync: this is a no-network readiness check for future connector scheduling work.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check connector sync readiness without outbound network calls.")
    parser.add_argument(
        "--connector",
        action="append",
        choices=sorted(SUPPORTED_CONNECTORS),
        help="Connector to check. Repeat for multiple connectors. Defaults to all supported connectors.",
    )
    parser.add_argument("--payload-dir", help="Directory containing <connector>.json local export payloads.")
    parser.add_argument("--source-url", help="Optional future vendor source URL to validate without connecting.")
    parser.add_argument("--odbc-connection-string", help="Optional future ODBC connection string to validate without connecting.")
    parser.add_argument("--print-only", action="store_true", help="Print the readiness plan without checking inputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    connectors = args.connector or sorted(SUPPORTED_CONNECTORS)
    payload_dir = Path(args.payload_dir) if args.payload_dir else None
    if args.print_only:
        _print_plan(connectors, payload_dir)
        return 0
    return _print_report(
        build_checks(
            connectors=connectors,
            payload_dir=payload_dir,
            source_url=args.source_url,
            odbc_connection_string=args.odbc_connection_string,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
