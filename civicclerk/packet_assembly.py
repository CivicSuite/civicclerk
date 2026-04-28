"""Database-backed packet assembly records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiccore.audit import AuditActor, AuditHashChain, AuditSubject


class PacketAssemblyStatus(StrEnum):
    """Staff-facing packet assembly state."""

    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


metadata = sa.MetaData()

packet_assembly_records = sa.Table(
    "packet_assembly_records",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("meeting_id", sa.String(64), nullable=False),
    sa.Column("packet_snapshot_id", sa.String(64), nullable=False),
    sa.Column("packet_version", sa.Integer(), nullable=False),
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("actor", sa.String(255), nullable=False),
    sa.Column("agenda_item_ids", sa.JSON(), nullable=False),
    sa.Column("source_references", sa.JSON(), nullable=False),
    sa.Column("citations", sa.JSON(), nullable=False),
    sa.Column("finalized_by", sa.String(255), nullable=True),
    sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_audit_hash", sa.String(128), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)


@dataclass(frozen=True)
class PacketAssemblyRecord:
    """One persisted packet assembly draft or finalized packet record."""

    id: str
    meeting_id: str
    packet_snapshot_id: str
    packet_version: int
    title: str
    status: str
    actor: str
    agenda_item_ids: list[str]
    source_references: list[dict]
    citations: list[dict]
    finalized_by: str | None
    finalized_at: datetime | None
    last_audit_hash: str
    created_at: datetime
    updated_at: datetime

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "packet_snapshot_id": self.packet_snapshot_id,
            "packet_version": self.packet_version,
            "title": self.title,
            "status": self.status,
            "actor": self.actor,
            "agenda_item_ids": self.agenda_item_ids,
            "source_references": self.source_references,
            "citations": self.citations,
            "finalized_by": self.finalized_by,
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
            "last_audit_hash": self.last_audit_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PacketAssemblyRepository:
    """SQLAlchemy-backed packet assembly record store."""

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
        metadata.create_all(self.engine)
        self.audit_chain = AuditHashChain()

    def create_draft(
        self,
        *,
        meeting_id: str,
        packet_snapshot_id: str,
        packet_version: int,
        title: str,
        actor: str,
        agenda_item_ids: list[str],
        source_references: list[dict],
        citations: list[dict],
    ) -> PacketAssemblyRecord:
        now = datetime.now(UTC)
        record_id = str(uuid4())
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="staff"),
            action="packet_assembly.created",
            subject=AuditSubject(subject_id=record_id, subject_type="packet_assembly_record"),
            source_module="civicclerk",
            metadata={
                "meeting_id": meeting_id,
                "packet_snapshot_id": packet_snapshot_id,
                "packet_version": packet_version,
                "source_count": len(source_references),
                "citation_count": len(citations),
            },
        )
        values = {
            "id": record_id,
            "meeting_id": meeting_id,
            "packet_snapshot_id": packet_snapshot_id,
            "packet_version": packet_version,
            "title": title,
            "status": PacketAssemblyStatus.DRAFT.value,
            "actor": actor,
            "agenda_item_ids": agenda_item_ids,
            "source_references": source_references,
            "citations": citations,
            "finalized_by": None,
            "finalized_at": None,
            "last_audit_hash": event.current_hash or "",
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(packet_assembly_records.insert().values(**values))
        return self.get(record_id) or _row_to_record(values)

    def get(self, record_id: str) -> PacketAssemblyRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(packet_assembly_records).where(packet_assembly_records.c.id == record_id)
            ).mappings().first()
        return _row_to_record(row) if row is not None else None

    def list_for_meeting(self, meeting_id: str) -> list[PacketAssemblyRecord]:
        statement = (
            sa.select(packet_assembly_records)
            .where(packet_assembly_records.c.meeting_id == meeting_id)
            .order_by(packet_assembly_records.c.packet_version)
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_record(row) for row in rows]

    def finalize(self, *, record_id: str, actor: str) -> PacketAssemblyRecord | None:
        existing = self.get(record_id)
        if existing is None:
            return None
        now = datetime.now(UTC)
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="staff"),
            action="packet_assembly.finalized",
            subject=AuditSubject(subject_id=record_id, subject_type="packet_assembly_record"),
            source_module="civicclerk",
            metadata={
                "meeting_id": existing.meeting_id,
                "packet_snapshot_id": existing.packet_snapshot_id,
                "packet_version": existing.packet_version,
            },
        )
        with self.engine.begin() as connection:
            connection.execute(
                packet_assembly_records.update()
                .where(packet_assembly_records.c.id == record_id)
                .values(
                    status=PacketAssemblyStatus.FINALIZED.value,
                    finalized_by=actor,
                    finalized_at=now,
                    updated_at=now,
                    last_audit_hash=event.current_hash or "",
                )
            )
        return self.get(record_id)


def _row_to_record(row) -> PacketAssemblyRecord:
    data = dict(row)
    return PacketAssemblyRecord(
        id=data["id"],
        meeting_id=data["meeting_id"],
        packet_snapshot_id=data["packet_snapshot_id"],
        packet_version=data["packet_version"],
        title=data["title"],
        status=data["status"],
        actor=data["actor"],
        agenda_item_ids=list(data["agenda_item_ids"]),
        source_references=list(data["source_references"]),
        citations=list(data["citations"]),
        finalized_by=data["finalized_by"],
        finalized_at=data["finalized_at"],
        last_audit_hash=data["last_audit_hash"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


__all__ = [
    "PacketAssemblyRecord",
    "PacketAssemblyRepository",
    "PacketAssemblyStatus",
    "packet_assembly_records",
]
