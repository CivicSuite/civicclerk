"""Database-backed notice checklist and posting-proof records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiccore.audit import AuditActor, AuditHashChain, AuditSubject


class NoticeChecklistStatus(StrEnum):
    """Notice checklist workflow state."""

    CHECKED = "CHECKED"
    POSTED = "POSTED"


metadata = sa.MetaData()

notice_checklist_records = sa.Table(
    "notice_checklist_records",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("meeting_id", sa.String(64), nullable=False),
    sa.Column("notice_type", sa.String(120), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("compliant", sa.Boolean(), nullable=False),
    sa.Column("http_status", sa.Integer(), nullable=False),
    sa.Column("warnings", sa.JSON(), nullable=False),
    sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("minimum_notice_hours", sa.Integer(), nullable=False),
    sa.Column("statutory_basis", sa.Text(), nullable=True),
    sa.Column("approved_by", sa.String(255), nullable=True),
    sa.Column("posting_proof", sa.JSON(), nullable=True),
    sa.Column("last_audit_hash", sa.String(128), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)


@dataclass(frozen=True)
class NoticeChecklistRecord:
    """Persisted notice compliance check and optional posting proof."""

    id: str
    meeting_id: str
    notice_type: str
    status: str
    compliant: bool
    http_status: int
    warnings: list[dict]
    deadline_at: datetime
    posted_at: datetime
    minimum_notice_hours: int
    statutory_basis: str | None
    approved_by: str | None
    posting_proof: dict | None
    last_audit_hash: str
    created_at: datetime
    updated_at: datetime

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "notice_type": self.notice_type,
            "status": self.status,
            "compliant": self.compliant,
            "http_status": self.http_status,
            "warnings": self.warnings,
            "deadline_at": self.deadline_at.isoformat(),
            "posted_at": self.posted_at.isoformat(),
            "minimum_notice_hours": self.minimum_notice_hours,
            "statutory_basis": self.statutory_basis,
            "approved_by": self.approved_by,
            "posting_proof": self.posting_proof,
            "last_audit_hash": self.last_audit_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class NoticeChecklistRepository:
    """SQLAlchemy-backed notice checklist store."""

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

    def record_check(
        self,
        *,
        meeting_id: str,
        notice_type: str,
        compliant: bool,
        http_status: int,
        warnings: list[dict],
        deadline_at: datetime,
        posted_at: datetime,
        minimum_notice_hours: int,
        statutory_basis: str | None,
        approved_by: str | None,
        actor: str,
    ) -> NoticeChecklistRecord:
        now = datetime.now(UTC)
        record_id = str(uuid4())
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="staff"),
            action="notice_checklist.checked",
            subject=AuditSubject(subject_id=record_id, subject_type="notice_checklist_record"),
            source_module="civicclerk",
            metadata={
                "meeting_id": meeting_id,
                "notice_type": notice_type,
                "compliant": compliant,
                "warning_count": len(warnings),
            },
        )
        values = {
            "id": record_id,
            "meeting_id": meeting_id,
            "notice_type": notice_type,
            "status": NoticeChecklistStatus.CHECKED.value,
            "compliant": compliant,
            "http_status": http_status,
            "warnings": warnings,
            "deadline_at": deadline_at,
            "posted_at": posted_at,
            "minimum_notice_hours": minimum_notice_hours,
            "statutory_basis": statutory_basis,
            "approved_by": approved_by,
            "posting_proof": None,
            "last_audit_hash": event.current_hash or "",
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(notice_checklist_records.insert().values(**values))
        return self.get(record_id) or _row_to_record(values)

    def get(self, record_id: str) -> NoticeChecklistRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(notice_checklist_records).where(notice_checklist_records.c.id == record_id)
            ).mappings().first()
        return _row_to_record(row) if row is not None else None

    def list_for_meeting(self, meeting_id: str) -> list[NoticeChecklistRecord]:
        statement = (
            sa.select(notice_checklist_records)
            .where(notice_checklist_records.c.meeting_id == meeting_id)
            .order_by(notice_checklist_records.c.created_at)
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_record(row) for row in rows]

    def attach_posting_proof(
        self,
        *,
        record_id: str,
        actor: str,
        posting_proof: dict,
    ) -> NoticeChecklistRecord | None:
        existing = self.get(record_id)
        if existing is None:
            return None
        now = datetime.now(UTC)
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="staff"),
            action="notice_checklist.proof_attached",
            subject=AuditSubject(subject_id=record_id, subject_type="notice_checklist_record"),
            source_module="civicclerk",
            metadata={
                "meeting_id": existing.meeting_id,
                "notice_type": existing.notice_type,
                "proof_keys": sorted(posting_proof),
            },
        )
        with self.engine.begin() as connection:
            connection.execute(
                notice_checklist_records.update()
                .where(notice_checklist_records.c.id == record_id)
                .values(
                    status=NoticeChecklistStatus.POSTED.value,
                    posting_proof=posting_proof,
                    updated_at=now,
                    last_audit_hash=event.current_hash or "",
                )
            )
        return self.get(record_id)


def _row_to_record(row) -> NoticeChecklistRecord:
    data = dict(row)
    return NoticeChecklistRecord(
        id=data["id"],
        meeting_id=data["meeting_id"],
        notice_type=data["notice_type"],
        status=data["status"],
        compliant=data["compliant"],
        http_status=data["http_status"],
        warnings=list(data["warnings"]),
        deadline_at=data["deadline_at"],
        posted_at=data["posted_at"],
        minimum_notice_hours=data["minimum_notice_hours"],
        statutory_basis=data["statutory_basis"],
        approved_by=data["approved_by"],
        posting_proof=data["posting_proof"],
        last_audit_hash=data["last_audit_hash"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


__all__ = [
    "NoticeChecklistRecord",
    "NoticeChecklistRepository",
    "NoticeChecklistStatus",
    "notice_checklist_records",
]
