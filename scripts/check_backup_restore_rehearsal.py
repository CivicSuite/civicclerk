"""Rehearse CivicClerk backup/restore using local SQLite stores.

The helper creates deterministic source data, copies database and export files
into a backup directory, restores them to a separate directory, and verifies the
restored repositories can read the seeded records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REHEARSAL_ROOT = ROOT / ".backup-restore-rehearsal"
STORE_FILES = {
    "CIVICCLERK_AGENDA_INTAKE_DB_URL": "agenda-intake.db",
    "CIVICCLERK_AGENDA_ITEM_DB_URL": "agenda-items.db",
    "CIVICCLERK_MEETING_DB_URL": "meetings.db",
    "CIVICCLERK_PACKET_ASSEMBLY_DB_URL": "packet-assembly.db",
    "CIVICCLERK_NOTICE_CHECKLIST_DB_URL": "notice-checklist.db",
}


@dataclass(frozen=True)
class SeededIds:
    agenda_intake_id: str
    agenda_item_id: str
    meeting_id: str
    packet_assembly_id: str
    notice_checklist_id: str


def _sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.resolve().as_posix()}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise RuntimeError(
            f"Refusing to overwrite existing restore target: {destination}. "
            "Choose a new --run-id or remove the directory yourself after saving any needed data."
        )
    shutil.copytree(source, destination)


def _seed_source_data(source_data: Path, source_exports: Path) -> SeededIds:
    from civicclerk.agenda_intake import AgendaIntakeRepository
    from civicclerk.agenda_lifecycle import AgendaItemRepository
    from civicclerk.meeting_lifecycle import MeetingStore
    from civicclerk.notice_checklist import NoticeChecklistRepository
    from civicclerk.packet_assembly import PacketAssemblyRepository

    source_data.mkdir(parents=True, exist_ok=True)
    source_exports.mkdir(parents=True, exist_ok=True)

    agenda_intake = AgendaIntakeRepository(
        db_url=_sqlite_url(source_data / STORE_FILES["CIVICCLERK_AGENDA_INTAKE_DB_URL"])
    )
    intake_item = agenda_intake.submit(
        title="Backup rehearsal zoning update",
        department_name="Planning",
        submitted_by="planner@example.gov",
        summary="Seeded agenda intake record for backup/restore rehearsal.",
        source_references=[{"system": "civicclerk-rehearsal", "id": "INTAKE-001"}],
    )
    agenda_intake.review(
        item_id=intake_item.id,
        reviewer="clerk@example.gov",
        ready=True,
        notes="Ready for restore verification.",
    )

    agenda_items = AgendaItemRepository(
        db_url=_sqlite_url(source_data / STORE_FILES["CIVICCLERK_AGENDA_ITEM_DB_URL"])
    )
    agenda_item = agenda_items.create(
        title="Backup rehearsal action item",
        department_name="Clerk",
    )
    agenda_items.transition(
        item_id=agenda_item.id,
        to_status="SUBMITTED",
        actor="clerk@example.gov",
    )

    meetings = MeetingStore(db_url=_sqlite_url(source_data / STORE_FILES["CIVICCLERK_MEETING_DB_URL"]))
    meeting = meetings.create(
        title="Backup Restore Rehearsal Council Meeting",
        meeting_type="regular",
        scheduled_start=datetime(2026, 5, 5, 18, 0, tzinfo=UTC),
    )

    packets = PacketAssemblyRepository(
        db_url=_sqlite_url(source_data / STORE_FILES["CIVICCLERK_PACKET_ASSEMBLY_DB_URL"])
    )
    packet = packets.create_draft(
        meeting_id=meeting.id,
        packet_snapshot_id="snapshot-backup-restore-001",
        packet_version=1,
        title="Backup restore rehearsal packet",
        actor="clerk@example.gov",
        agenda_item_ids=[agenda_item.id],
        source_references=[{"system": "civicclerk-rehearsal", "id": agenda_item.id}],
        citations=[{"label": "Agenda item", "source": "seeded rehearsal data"}],
    )
    packets.finalize(record_id=packet.id, actor="clerk@example.gov")

    notices = NoticeChecklistRepository(
        db_url=_sqlite_url(source_data / STORE_FILES["CIVICCLERK_NOTICE_CHECKLIST_DB_URL"])
    )
    notice = notices.record_check(
        meeting_id=meeting.id,
        notice_type="regular",
        compliant=True,
        http_status=200,
        warnings=[],
        deadline_at=datetime(2026, 5, 4, 18, 0, tzinfo=UTC),
        posted_at=datetime(2026, 5, 4, 12, 0, tzinfo=UTC),
        minimum_notice_hours=24,
        statutory_basis="Local open meeting notice rehearsal",
        approved_by="clerk@example.gov",
        actor="clerk@example.gov",
    )
    notices.attach_posting_proof(
        record_id=notice.id,
        actor="clerk@example.gov",
        posting_proof={
            "url": "https://example.gov/notices/backup-restore-rehearsal",
            "captured_at": datetime(2026, 5, 4, 12, 5, tzinfo=UTC).isoformat(),
        },
    )

    export_dir = source_exports / "backup-restore-rehearsal-packet"
    export_dir.mkdir(parents=True, exist_ok=True)
    export_manifest = {
        "bundle_name": "backup-restore-rehearsal-packet",
        "meeting_id": meeting.id,
        "packet_assembly_id": packet.id,
        "created_at": datetime.now(UTC).isoformat(),
        "files": ["packet-summary.txt"],
    }
    (export_dir / "manifest.json").write_text(
        json.dumps(export_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (export_dir / "packet-summary.txt").write_text(
        "Backup restore rehearsal packet export evidence.\n",
        encoding="utf-8",
    )

    return SeededIds(
        agenda_intake_id=intake_item.id,
        agenda_item_id=agenda_item.id,
        meeting_id=meeting.id,
        packet_assembly_id=packet.id,
        notice_checklist_id=notice.id,
    )


def _build_backup(run_root: Path, source_data: Path, source_exports: Path, seeded: SeededIds) -> Path:
    backup_root = run_root / "backup"
    backup_data = backup_root / "data"
    backup_exports = backup_root / "exports"
    backup_data.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, str | int]] = []
    for filename in STORE_FILES.values():
        source = source_data / filename
        destination = backup_data / filename
        _copy_file(source, destination)
        files.append(
            {
                "path": destination.relative_to(backup_root).as_posix(),
                "source": source.relative_to(run_root).as_posix(),
                "size": destination.stat().st_size,
                "sha256": _sha256(destination),
            }
        )

    _copy_tree(source_exports, backup_exports)
    for export_file in sorted(path for path in backup_exports.rglob("*") if path.is_file()):
        files.append(
            {
                "path": export_file.relative_to(backup_root).as_posix(),
                "source": (source_exports / export_file.relative_to(backup_exports)).relative_to(run_root).as_posix(),
                "size": export_file.stat().st_size,
                "sha256": _sha256(export_file),
            }
        )

    manifest = {
        "service": "civicclerk",
        "created_at": datetime.now(UTC).isoformat(),
        "stores": STORE_FILES,
        "seeded_ids": seeded.__dict__,
        "files": files,
    }
    manifest_path = backup_root / "civicclerk-backup-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def _restore_backup(run_root: Path) -> tuple[Path, Path]:
    backup_root = run_root / "backup"
    restored_data = run_root / "restored-data"
    restored_exports = run_root / "restored-exports"
    restored_data.mkdir(parents=True, exist_ok=True)

    for filename in STORE_FILES.values():
        _copy_file(backup_root / "data" / filename, restored_data / filename)
    _copy_tree(backup_root / "exports", restored_exports)
    return restored_data, restored_exports


def _verify_restored_data(
    *,
    source_data: Path,
    source_exports: Path,
    restored_data: Path,
    restored_exports: Path,
    seeded: SeededIds,
) -> list[str]:
    from civicclerk.agenda_intake import AgendaIntakeRepository
    from civicclerk.agenda_lifecycle import AgendaItemRepository
    from civicclerk.meeting_lifecycle import MeetingStore
    from civicclerk.notice_checklist import NoticeChecklistRepository
    from civicclerk.packet_assembly import PacketAssemblyRepository

    failures: list[str] = []
    for filename in STORE_FILES.values():
        source = source_data / filename
        restored = restored_data / filename
        if not restored.exists():
            failures.append(f"missing restored database: {filename}")
        elif _sha256(source) != _sha256(restored):
            failures.append(f"checksum mismatch after restore: {filename}")

    source_export_files = sorted(path.relative_to(source_exports) for path in source_exports.rglob("*") if path.is_file())
    restored_export_files = sorted(
        path.relative_to(restored_exports) for path in restored_exports.rglob("*") if path.is_file()
    )
    if source_export_files != restored_export_files:
        failures.append("restored export file list does not match source exports")
    for relative_path in source_export_files:
        if _sha256(source_exports / relative_path) != _sha256(restored_exports / relative_path):
            failures.append(f"export checksum mismatch after restore: {relative_path.as_posix()}")

    agenda_intake = AgendaIntakeRepository(
        db_url=_sqlite_url(restored_data / STORE_FILES["CIVICCLERK_AGENDA_INTAKE_DB_URL"])
    )
    if agenda_intake.get(seeded.agenda_intake_id) is None:
        failures.append("restored agenda intake record is unreadable")

    agenda_items = AgendaItemRepository(
        db_url=_sqlite_url(restored_data / STORE_FILES["CIVICCLERK_AGENDA_ITEM_DB_URL"])
    )
    agenda_item = agenda_items.get(seeded.agenda_item_id)
    if agenda_item is None or agenda_item.status != "SUBMITTED":
        failures.append("restored agenda item status is not SUBMITTED")

    meetings = MeetingStore(db_url=_sqlite_url(restored_data / STORE_FILES["CIVICCLERK_MEETING_DB_URL"]))
    if meetings.get(seeded.meeting_id) is None:
        failures.append("restored meeting record is unreadable")

    packets = PacketAssemblyRepository(
        db_url=_sqlite_url(restored_data / STORE_FILES["CIVICCLERK_PACKET_ASSEMBLY_DB_URL"])
    )
    packet = packets.get(seeded.packet_assembly_id)
    if packet is None or packet.status != "FINALIZED":
        failures.append("restored packet assembly record is not FINALIZED")

    notices = NoticeChecklistRepository(
        db_url=_sqlite_url(restored_data / STORE_FILES["CIVICCLERK_NOTICE_CHECKLIST_DB_URL"])
    )
    notice = notices.get(seeded.notice_checklist_id)
    if notice is None or not notice.posting_proof:
        failures.append("restored notice checklist posting proof is missing")

    if not (restored_exports / "backup-restore-rehearsal-packet" / "manifest.json").exists():
        failures.append("restored packet export manifest is missing")

    return failures


def _print_plan(run_root: Path, *, strict: bool) -> None:
    restored_data = run_root / "restored-data"
    restored_exports = run_root / "restored-exports"
    print("CivicClerk backup/restore rehearsal")
    print(f"Rehearsal root: {run_root}")
    print("Source stores: source-data/*.db")
    print("Backup manifest: backup/civicclerk-backup-manifest.json")
    print("Restored stores: restored-data/*.db")
    print(f"Strict mode: {'on' if strict else 'off'}")
    print("Environment to run restored app after rehearsal:")
    for env_var, filename in STORE_FILES.items():
        print(f"  {env_var}={_sqlite_url(restored_data / filename)}")
    print(f"  CIVICCLERK_EXPORT_ROOT={restored_exports}")
    print("Verification: checks database checksums, export checksums, and readable restored workflow records.")
    print("If a check fails: keep the run directory, inspect the named file, fix the backup source, then rerun with a new --run-id.")


def run_rehearsal(run_root: Path, *, strict: bool) -> int:
    if run_root.exists():
        print(f"FAILED: rehearsal run already exists: {run_root}")
        print("Fix: choose a new --run-id or move the existing run aside before retrying.")
        return 1

    source_data = run_root / "source-data"
    source_exports = run_root / "source-exports"
    try:
        seeded = _seed_source_data(source_data, source_exports)
        manifest_path = _build_backup(run_root, source_data, source_exports, seeded)
        restored_data, restored_exports = _restore_backup(run_root)
        failures = _verify_restored_data(
            source_data=source_data,
            source_exports=source_exports,
            restored_data=restored_data,
            restored_exports=restored_exports,
            seeded=seeded,
        )
    except Exception as exc:
        print(f"FAILED: backup/restore rehearsal raised {exc.__class__.__name__}: {exc}")
        print("Fix: keep the rehearsal directory for inspection, resolve the named failure, then rerun with a new --run-id.")
        return 1

    print("CivicClerk backup/restore rehearsal")
    print(f"Run root: {run_root}")
    print(f"[PASS] source stores seeded: {len(STORE_FILES)} SQLite databases")
    print(f"[PASS] backup manifest written: {manifest_path.relative_to(run_root).as_posix()}")
    print("[PASS] restored stores copied to restored-data")
    print("[PASS] restored packet export copied to restored-exports")
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print("BACKUP-RESTORE-REHEARSAL: FAILED")
        return 1
    print("[PASS] restored records reopened through CivicClerk repositories")
    print("BACKUP-RESTORE-REHEARSAL: PASSED")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local CivicClerk backup/restore rehearsal.")
    parser.add_argument("--rehearsal-root", default=str(DEFAULT_REHEARSAL_ROOT))
    parser.add_argument(
        "--run-id",
        default=datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S"),
        help="Subdirectory name under --rehearsal-root. Defaults to a timestamped run id.",
    )
    parser.add_argument("--print-only", action="store_true", help="Print the plan without creating files.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when any rehearsal check fails.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_root = (Path(args.rehearsal_root) / args.run_id).resolve()
    if args.print_only:
        _print_plan(run_root, strict=args.strict)
        return 0
    result = run_rehearsal(run_root, strict=args.strict)
    if args.strict:
        return result
    return 0 if result == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
