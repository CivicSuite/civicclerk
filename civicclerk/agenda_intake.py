"""Database-backed agenda intake queue and clerk readiness review."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiccore.audit import AuditActor, AuditHashChain, AuditSubject


class AgendaReadinessStatus(StrEnum):
    """Clerk review status for department-submitted agenda intake items."""

    PENDING = "PENDING"
    READY = "READY"
    NEEDS_REVISION = "NEEDS_REVISION"


metadata = sa.MetaData()

agenda_intake_queue = sa.Table(
    "agenda_intake_queue",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("department_name", sa.String(255), nullable=False),
    sa.Column("submitted_by", sa.String(255), nullable=False),
    sa.Column("summary", sa.Text(), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("readiness_status", sa.String(80), nullable=False),
    sa.Column("reviewer", sa.String(255), nullable=True),
    sa.Column("review_notes", sa.Text(), nullable=True),
    sa.Column("source_references", sa.JSON(), nullable=False),
    sa.Column("last_audit_hash", sa.String(128), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)


@dataclass(frozen=True)
class AgendaIntakeItem:
    """Department-submitted item waiting for staff readiness review."""

    id: str
    title: str
    department_name: str
    submitted_by: str
    summary: str
    status: str
    readiness_status: str
    source_references: list[dict]
    reviewer: str | None
    review_notes: str | None
    last_audit_hash: str
    created_at: datetime
    updated_at: datetime

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "department_name": self.department_name,
            "submitted_by": self.submitted_by,
            "summary": self.summary,
            "status": self.status,
            "readiness_status": self.readiness_status,
            "source_references": self.source_references,
            "reviewer": self.reviewer,
            "review_notes": self.review_notes,
            "last_audit_hash": self.last_audit_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AgendaIntakeRepository:
    """SQLAlchemy-backed agenda intake queue.

    The default application wiring can use SQLite for local demos or any
    SQLAlchemy URL supplied by `CIVICCLERK_AGENDA_INTAKE_DB_URL`. The repository
    is deliberately small: it proves persistence and review semantics before
    the full staff UI workflow lands.
    """

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

    def submit(
        self,
        *,
        title: str,
        department_name: str,
        submitted_by: str,
        summary: str,
        source_references: list[dict],
    ) -> AgendaIntakeItem:
        now = datetime.now(UTC)
        item_id = str(uuid4())
        values = {
            "id": item_id,
            "title": title,
            "department_name": department_name,
            "submitted_by": submitted_by,
            "summary": summary,
            "status": "SUBMITTED",
            "readiness_status": AgendaReadinessStatus.PENDING.value,
            "reviewer": None,
            "review_notes": None,
            "source_references": source_references,
            "last_audit_hash": "",
            "created_at": now,
            "updated_at": now,
        }
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=submitted_by, actor_type="staff"),
            action="agenda_intake.submitted",
            subject=AuditSubject(subject_id=item_id, subject_type="agenda_intake_item"),
            source_module="civicclerk",
            metadata={
                "department_name": department_name,
                "source_count": len(source_references),
            },
        )
        values["last_audit_hash"] = event.current_hash or ""
        with self.engine.begin() as connection:
            connection.execute(agenda_intake_queue.insert().values(**values))
        return self.get(item_id) or _row_to_item(values)

    def get(self, item_id: str) -> AgendaIntakeItem | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(agenda_intake_queue).where(agenda_intake_queue.c.id == item_id)
            ).mappings().first()
        return _row_to_item(row) if row is not None else None

    def list_queue(self, *, readiness_status: str | None = None) -> list[AgendaIntakeItem]:
        statement = sa.select(agenda_intake_queue).order_by(agenda_intake_queue.c.created_at)
        if readiness_status is not None:
            statement = statement.where(agenda_intake_queue.c.readiness_status == readiness_status)
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_item(row) for row in rows]

    def review(
        self,
        *,
        item_id: str,
        reviewer: str,
        ready: bool,
        notes: str,
    ) -> AgendaIntakeItem | None:
        existing = self.get(item_id)
        if existing is None:
            return None
        readiness_status = (
            AgendaReadinessStatus.READY.value
            if ready
            else AgendaReadinessStatus.NEEDS_REVISION.value
        )
        status = "READY_FOR_CLERK" if ready else "NEEDS_REVISION"
        now = datetime.now(UTC)
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=reviewer, actor_type="clerk"),
            action="agenda_intake.reviewed",
            subject=AuditSubject(subject_id=item_id, subject_type="agenda_intake_item"),
            source_module="civicclerk",
            metadata={
                "ready": ready,
                "readiness_status": readiness_status,
                "notes": notes,
            },
        )
        with self.engine.begin() as connection:
            connection.execute(
                agenda_intake_queue.update()
                .where(agenda_intake_queue.c.id == item_id)
                .values(
                    status=status,
                    readiness_status=readiness_status,
                    reviewer=reviewer,
                    review_notes=notes,
                    last_audit_hash=event.current_hash or "",
                    updated_at=now,
                )
            )
        return self.get(item_id)


def _row_to_item(row) -> AgendaIntakeItem:
    data = dict(row)
    return AgendaIntakeItem(
        id=data["id"],
        title=data["title"],
        department_name=data["department_name"],
        submitted_by=data["submitted_by"],
        summary=data["summary"],
        status=data["status"],
        readiness_status=data["readiness_status"],
        source_references=list(data["source_references"]),
        reviewer=data["reviewer"],
        review_notes=data["review_notes"],
        last_audit_hash=data["last_audit_hash"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


__all__ = [
    "AgendaIntakeItem",
    "AgendaIntakeRepository",
    "AgendaReadinessStatus",
    "agenda_intake_queue",
]
