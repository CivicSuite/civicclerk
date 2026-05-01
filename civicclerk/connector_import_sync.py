"""Local connector import sync primitives shared by CLI and Celery workers."""

from __future__ import annotations

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


def payload_paths(payload_dir: Path, connector: str) -> list[Path]:
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
        attempts.extend(
            ImportAttempt(
                connector=connector,
                payload_path=payload_dir,
                ok=False,
                message=f"Unsupported connector '{connector}'.",
                fix=f"Use one of: {supported_list}.",
            )
            for connector in unknown
        )

    for connector in [connector for connector in connectors if connector in supported]:
        paths = payload_paths(payload_dir, connector)
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
            attempts.append(normalize_payload(connector=connector, payload_path=payload_path))

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps([attempt_dict(attempt) for attempt in attempts], indent=2) + "\n",
            encoding="utf-8",
        )
    return attempts


def normalize_payload(*, connector: str, payload_path: Path) -> ImportAttempt:
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8-sig"))
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


def attempt_dict(attempt: ImportAttempt) -> dict[str, Any]:
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
