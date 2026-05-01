"""Normalize local connector export payloads into a repeatable import ledger."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from civicclerk.connectors import ConnectorImportError, SUPPORTED_CONNECTORS, import_meeting_payload


@dataclass(frozen=True)
class ImportAttempt:
    connector: str
    payload_path: Path
    ok: bool
    message: str
    fix: str
    normalized: dict[str, Any] | None = None


def _payload_paths(payload_dir: Path, connector: str) -> list[Path]:
    direct_payload = payload_dir / f"{connector}.json"
    connector_dir = payload_dir / connector
    paths: list[Path] = []
    if direct_payload.exists():
        paths.append(direct_payload)
    if connector_dir.exists():
        paths.extend(sorted(connector_dir.glob("*.json")))
    return paths


def run_import_sync(*, payload_dir: Path, connectors: list[str], output_path: Path | None) -> list[ImportAttempt]:
    attempts: list[ImportAttempt] = []
    supported = set(SUPPORTED_CONNECTORS)
    unknown = [connector for connector in connectors if connector not in supported]
    if unknown:
        supported_list = ", ".join(sorted(supported))
        return [
            ImportAttempt(
                connector=connector,
                payload_path=payload_dir,
                ok=False,
                message=f"Unsupported connector '{connector}'.",
                fix=f"Use one of: {supported_list}.",
            )
            for connector in unknown
        ]

    for connector in connectors:
        paths = _payload_paths(payload_dir, connector)
        if not paths:
            attempts.append(
                ImportAttempt(
                    connector=connector,
                    payload_path=payload_dir / f"{connector}.json",
                    ok=False,
                    message=f"No local payloads found for {connector}.",
                    fix=f"Export {connector}.json or one or more {connector}/*.json files, then retry.",
                )
            )
            continue
        for payload_path in paths:
            attempts.append(_normalize_payload(connector=connector, payload_path=payload_path))

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps([_attempt_dict(attempt) for attempt in attempts], indent=2) + "\n",
            encoding="utf-8",
        )
    return attempts


def _normalize_payload(*, connector: str, payload_path: Path) -> ImportAttempt:
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        imported = import_meeting_payload(connector_name=connector, payload=payload)
    except FileNotFoundError as exc:
        return ImportAttempt(
            connector=connector,
            payload_path=payload_path,
            ok=False,
            message=str(exc),
            fix=f"Export a readable {connector} JSON payload, then retry.",
        )
    except json.JSONDecodeError as exc:
        return ImportAttempt(
            connector=connector,
            payload_path=payload_path,
            ok=False,
            message=f"{payload_path.name} is not valid JSON: {exc.msg}.",
            fix="Export valid JSON from the source agenda system and retry.",
        )
    except ConnectorImportError as exc:
        public_error = exc.public_dict()
        return ImportAttempt(
            connector=connector,
            payload_path=payload_path,
            ok=False,
            message=public_error["message"],
            fix=public_error["fix"],
        )

    normalized = imported.public_dict()
    return ImportAttempt(
        connector=connector,
        payload_path=payload_path,
        ok=True,
        message=(
            f"normalized meeting {normalized['external_meeting_id']} "
            f"with {len(normalized['agenda_items'])} agenda item(s)."
        ),
        fix="Review source provenance before promoting imported items into clerk workflows.",
        normalized=normalized,
    )


def _attempt_dict(attempt: ImportAttempt) -> dict[str, Any]:
    result: dict[str, Any] = {
        "connector": attempt.connector,
        "payload_path": str(attempt.payload_path),
        "ok": attempt.ok,
        "message": attempt.message,
        "fix": attempt.fix,
    }
    if attempt.normalized is not None:
        result["normalized"] = attempt.normalized
    return result


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
