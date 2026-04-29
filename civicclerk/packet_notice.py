"""Packet snapshot, export bundle, and notice compliance helpers for CivicClerk."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from civicclerk import __version__ as CIVICCLERK_VERSION
from civiccore import __version__ as CIVICCORE_VERSION
from civiccore.audit import AuditActor, AuditHashChain, AuditSubject
from civiccore.exports import BundleFile, ExportBundle, build_sha256sums, validate_bundle, write_manifest
from civiccore.provenance import ProvenanceBundle, SourceKind, SourceReference


SPECIAL_NOTICE_TYPES = {"special", "emergency"}
PUBLIC_BLOCKED_SENSITIVITY = {"closed_session", "staff_only", "restricted"}


class PacketExportError(ValueError):
    """Raised when a packet export would violate public-record guardrails."""

    def __init__(self, *, code: str, message: str, fix: str, http_status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fix = fix
        self.http_status = http_status

    def public_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "fix": self.fix,
        }


@dataclass(frozen=True)
class PacketSource:
    """Source material included in an exported packet bundle."""

    source_id: str
    title: str
    kind: str = "document"
    source_system: str | None = None
    source_path: str | None = None
    checksum: str | None = None
    sensitivity_label: str | None = None
    citation_label: str | None = None

    def to_reference(self) -> SourceReference:
        try:
            source_kind = SourceKind(self.kind)
        except ValueError as exc:
            raise PacketExportError(
                code="unsupported_source_kind",
                message=f"Packet source kind {self.kind!r} is not supported.",
                fix="Use a CivicCore source kind such as document, record, meeting_packet, code_section, zoning_parcel, local_file, or url.",
            ) from exc
        return SourceReference(
            source_id=self.source_id,
            kind=source_kind,
            title=self.title,
            source_system=self.source_system,
            source_path=self.source_path,
            checksum=self.checksum,
            sensitivity_label=self.sensitivity_label,
            citation_locator={"label": self.citation_label} if self.citation_label else None,
        )


@dataclass(frozen=True)
class PacketSnapshot:
    id: str
    meeting_id: str
    version: int
    agenda_item_ids: tuple[str, ...]
    actor: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "version": self.version,
            "agenda_item_ids": list(self.agenda_item_ids),
            "actor": self.actor,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class PacketExportResult:
    """Result of creating a records-ready packet export bundle."""

    meeting_id: str
    bundle_path: str
    manifest_path: str
    checksums_path: str
    civiccore_version: str
    packet_version: int
    audit_hash: str
    generated_files: tuple[str, ...]

    def public_dict(self) -> dict:
        return {
            "meeting_id": self.meeting_id,
            "bundle_path": self.bundle_path,
            "manifest_path": self.manifest_path,
            "checksums_path": self.checksums_path,
            "civiccore_version": self.civiccore_version,
            "packet_version": self.packet_version,
            "audit_hash": self.audit_hash,
            "generated_files": list(self.generated_files),
        }


class PacketStore:
    """Packet version and export-bundle store.

    The store is still process-local in this slice, but export bundles are
    written to disk with CivicCore v0.8.0 manifests, checksums, provenance, and
    hash-chained audit events so they can be validated without the server.
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, list[PacketSnapshot]] = {}
        self.audit_chain = AuditHashChain()

    def create_snapshot(
        self,
        *,
        meeting_id: str,
        agenda_item_ids: list[str],
        actor: str,
    ) -> PacketSnapshot:
        existing = self._snapshots.setdefault(meeting_id, [])
        snapshot = PacketSnapshot(
            id=str(uuid4()),
            meeting_id=meeting_id,
            version=len(existing) + 1,
            agenda_item_ids=tuple(agenda_item_ids),
            actor=actor,
        )
        existing.append(snapshot)
        self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="staff"),
            action="packet_snapshot.created",
            subject=AuditSubject(subject_id=snapshot.id, subject_type="packet_snapshot"),
            source_module="civicclerk",
            metadata={
                "meeting_id": meeting_id,
                "version": snapshot.version,
                "agenda_item_ids": list(snapshot.agenda_item_ids),
            },
        )
        return snapshot

    def list_snapshots(self, meeting_id: str) -> list[PacketSnapshot]:
        return list(self._snapshots.get(meeting_id, []))

    def create_export_bundle(
        self,
        *,
        meeting_id: str,
        meeting_title: str,
        bundle_path: str | Path,
        actor: str,
        sources: list[PacketSource],
        notices: list[dict] | None = None,
        public_bundle: bool = True,
    ) -> PacketExportResult:
        snapshots = self._snapshots.get(meeting_id, [])
        if not snapshots:
            raise PacketExportError(
                code="packet_snapshot_required",
                message="Packet export requires at least one packet snapshot.",
                fix="Create a packet snapshot before exporting the records-ready bundle.",
            )
        if not sources:
            raise PacketExportError(
                code="source_provenance_required",
                message="Packet export requires at least one source reference.",
                fix="Attach source/provenance metadata before exporting the bundle.",
            )

        source_refs = [source.to_reference() for source in sources]
        if public_bundle:
            blocked = [
                source
                for source in source_refs
                if (source.sensitivity_label or "").strip().lower() in PUBLIC_BLOCKED_SENSITIVITY
            ]
            if blocked:
                raise PacketExportError(
                    code="closed_session_source_not_public",
                    message="Public packet export cannot include closed-session or restricted source files.",
                    fix="Remove restricted sources or create a staff-only export bundle instead.",
                )

        root = Path(bundle_path)
        root.mkdir(parents=True, exist_ok=True)
        snapshot = snapshots[-1]
        generated_at = datetime.now(UTC)
        provenance = ProvenanceBundle(
            bundle_id=f"civicclerk-{meeting_id}-packet-v{snapshot.version}",
            generated_at=generated_at,
            sources=source_refs,
        )

        packet_data = {
            "meeting_id": meeting_id,
            "meeting_title": meeting_title,
            "packet_version": snapshot.version,
            "agenda_item_ids": list(snapshot.agenda_item_ids),
            "generated_at": generated_at.isoformat(),
            "public_bundle": public_bundle,
            "sources": [source.model_dump(mode="json") for source in source_refs],
        }
        notice_data = {
            "meeting_id": meeting_id,
            "notices": notices or [],
            "generated_at": generated_at.isoformat(),
        }

        _write_json(root / "packet.json", packet_data)
        _write_json(root / "provenance.json", provenance.to_manifest())
        _write_json(root / "notices.json", notice_data)

        files = [
            BundleFile.from_path(root, "packet.json"),
            BundleFile.from_path(root, "provenance.json"),
            BundleFile.from_path(root, "notices.json"),
        ]
        bundle = ExportBundle(
            module_name="civicclerk",
            module_version=CIVICCLERK_VERSION,
            civiccore_version=CIVICCORE_VERSION,
            files=files,
            limitations=[
                "Export bundle is a static records-ready snapshot, not a legal sufficiency determination.",
                "Public bundles exclude closed-session and restricted source files.",
            ],
        )
        manifest = write_manifest(root, bundle)
        build_sha256sums(root, files)
        validate_bundle(root)

        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="staff"),
            action="packet_export_bundle.created",
            subject=AuditSubject(subject_id=meeting_id, subject_type="meeting"),
            source_module="civicclerk",
            metadata={
                "packet_version": snapshot.version,
                "bundle_path": str(root),
                "manifest_files": [file.path for file in manifest.generated_files],
                "public_bundle": public_bundle,
            },
        )
        return PacketExportResult(
            meeting_id=meeting_id,
            bundle_path=str(root),
            manifest_path=str(root / "manifest.json"),
            checksums_path=str(root / "SHA256SUMS.txt"),
            civiccore_version=manifest.civiccore_version,
            packet_version=snapshot.version,
            audit_hash=event.current_hash or "",
            generated_files=tuple(file.path for file in manifest.generated_files),
        )


@dataclass(frozen=True)
class NoticeComplianceResult:
    meeting_id: str
    notice_type: str
    scheduled_start: datetime
    posted_at: datetime
    minimum_notice_hours: int
    deadline_at: datetime
    statutory_basis: str | None
    approved_by: str | None
    compliant: bool
    http_status: int
    warnings: list[dict[str, str]]

    def public_dict(self) -> dict:
        return {
            "meeting_id": self.meeting_id,
            "notice_type": self.notice_type,
            "scheduled_start": self.scheduled_start.isoformat(),
            "posted_at": self.posted_at.isoformat(),
            "minimum_notice_hours": self.minimum_notice_hours,
            "deadline_at": self.deadline_at.isoformat(),
            "statutory_basis": self.statutory_basis,
            "approved_by": self.approved_by,
            "compliant": self.compliant,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class PostedNotice:
    id: str
    result: NoticeComplianceResult

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            **self.result.public_dict(),
            "posted": True,
        }


class NoticeStore:
    """In-memory posted notice store until DB-backed workflow persistence lands."""

    def __init__(self) -> None:
        self._notices: dict[str, list[PostedNotice]] = {}

    def create(self, result: NoticeComplianceResult) -> PostedNotice:
        notice = PostedNotice(id=str(uuid4()), result=result)
        self._notices.setdefault(result.meeting_id, []).append(notice)
        return notice

    def list_notices(self, meeting_id: str) -> list[PostedNotice]:
        return list(self._notices.get(meeting_id, []))


def evaluate_notice_compliance(
    *,
    meeting_id: str,
    notice_type: str,
    scheduled_start: datetime,
    posted_at: datetime,
    minimum_notice_hours: int,
    statutory_basis: str | None,
    approved_by: str | None,
) -> NoticeComplianceResult:
    normalized_notice_type = notice_type.strip().lower()
    deadline_at = scheduled_start - timedelta(hours=minimum_notice_hours)
    warnings: list[dict[str, str]] = []

    if normalized_notice_type in SPECIAL_NOTICE_TYPES and not statutory_basis:
        warnings.append(
            {
                "code": "missing_statutory_basis",
                "message": "Special and emergency notices require a statutory basis.",
                "fix": "Add the statutory basis authorizing this meeting type before posting public notice.",
            }
        )

    if posted_at > deadline_at:
        warnings.append(
            {
                "code": "notice_deadline_missed",
                "message": "Notice was posted after the required deadline.",
                "fix": "Move the meeting, document the legal exception, or obtain attorney/clerk approval before posting.",
            }
        )

    if not approved_by:
        warnings.append(
            {
                "code": "human_approval_required",
                "message": "Public notice posting requires a named clerk or authorized approver.",
                "fix": "Provide approved_by before posting public notice.",
            }
        )

    status = _status_for_warnings(warnings)
    return NoticeComplianceResult(
        meeting_id=meeting_id,
        notice_type=normalized_notice_type,
        scheduled_start=scheduled_start,
        posted_at=posted_at,
        minimum_notice_hours=minimum_notice_hours,
        deadline_at=deadline_at,
        statutory_basis=statutory_basis,
        approved_by=approved_by,
        compliant=not warnings,
        http_status=status,
        warnings=warnings,
    )


def _status_for_warnings(warnings: list[dict[str, str]]) -> int:
    if not warnings:
        return 200
    if warnings[0]["code"] == "human_approval_required":
        return 403
    return 422


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "NoticeComplianceResult",
    "NoticeStore",
    "PacketExportError",
    "PacketExportResult",
    "PacketSnapshot",
    "PacketSource",
    "PacketStore",
    "PostedNotice",
    "evaluate_notice_compliance",
]
