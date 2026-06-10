"""Public meeting calendar and archive helpers with permission-aware filtering."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiccore.audit import AuditActor, AuditHashChain, AuditSubject, record_event
from civiccore.search import (
    normalize_search_query,
    roles_grant_access,
    search_text_matches_query,
)


PUBLIC_VISIBILITY = "public"
CLOSED_SESSION_VISIBILITY = "closed_session"
PERMITTED_CLOSED_SESSION_ROLES = {"archive_reader", "city_attorney", "clerk_admin"}


@dataclass(frozen=True)
class PublicMeetingRecord:
    id: str
    meeting_id: str
    title: str
    visibility: str
    posted_agenda: str
    posted_packet: str
    approved_minutes: str
    public_comment_enabled: bool = False
    plain_language_summary: str | None = None
    agenda_download_url: str | None = None
    packet_download_url: str | None = None
    minutes_download_url: str | None = None
    minutes_adopted_at: str | None = None
    minutes_signed_by: str | None = None
    closed_session_notes: str | None = None

    def public_dict(self, *, include_closed: bool = False) -> dict[str, str | bool | None]:
        payload = {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "title": self.title,
            "posted_agenda": self.posted_agenda,
            "posted_packet": self.posted_packet,
            "approved_minutes": self.approved_minutes,
            "public_comment_enabled": self.public_comment_enabled,
            "plain_language_summary": self.plain_language_summary,
            "agenda_download_url": self.agenda_download_url,
            "packet_download_url": self.packet_download_url,
            "minutes_download_url": self.minutes_download_url,
            "minutes_adopted_at": self.minutes_adopted_at,
            "minutes_signed_by": self.minutes_signed_by,
        }
        if include_closed:
            payload["visibility"] = self.visibility
            payload["closed_session_notes"] = self.closed_session_notes
        return payload


@dataclass(frozen=True)
class PublicCommentRecord:
    id: str
    public_record_id: str
    commenter_name: str
    comment: str
    submitted_at: str
    status: str = "RECEIVED"

    def public_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "public_record_id": self.public_record_id,
            "commenter_name": self.commenter_name,
            "comment": self.comment,
            "submitted_at": self.submitted_at,
            "status": self.status,
        }


metadata = sa.MetaData()

public_meeting_records_table = sa.Table(
    "public_meeting_records",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("visibility", sa.String(80), nullable=False),
    sa.Column("posted_agenda", sa.Text(), nullable=False),
    sa.Column("posted_packet", sa.Text(), nullable=False),
    sa.Column("approved_minutes", sa.Text(), nullable=False),
    sa.Column("public_comment_enabled", sa.Boolean(), nullable=False),
    sa.Column("plain_language_summary", sa.Text(), nullable=True),
    sa.Column("agenda_download_url", sa.Text(), nullable=True),
    sa.Column("packet_download_url", sa.Text(), nullable=True),
    sa.Column("minutes_download_url", sa.Text(), nullable=True),
    sa.Column("minutes_adopted_at", sa.String(120), nullable=True),
    sa.Column("minutes_signed_by", sa.String(255), nullable=True),
    sa.Column("closed_session_notes", sa.Text(), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

public_comments_table = sa.Table(
    "public_comments",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("agenda_item_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("public_record_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("commenter_name", sa.String(255), nullable=False),
    sa.Column("body", sa.Text(), nullable=False),
    sa.Column("visibility", sa.String(80), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("moderation_notes", sa.Text(), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

# Existence-check mirror of canonical civicclerk.meetings (civicclerk/models.py).
# publish() pre-checks the meetings FK referent declared by migration 0014, so
# missing parents yield None instead of dialect-dependent orphans (SQLite) or
# raw IntegrityError (PostgreSQL). Only the id column is mirrored; migrated
# databases already have the full table and create_all() skips existing tables.
meetings_table = sa.Table(
    "meetings",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    schema="civicclerk",
)


class PublicArchiveStore:
    """In-memory public archive store until DB-backed archive persistence lands."""

    def __init__(self) -> None:
        self._records: dict[str, PublicMeetingRecord] = {}
        self._records_by_meeting: dict[str, str] = {}

    def publish(
        self,
        *,
        meeting_id: str,
        title: str,
        visibility: str,
        posted_agenda: str,
        posted_packet: str,
        approved_minutes: str,
        public_comment_enabled: bool = False,
        plain_language_summary: str | None = None,
        minutes_adopted_at: str | None = None,
        minutes_signed_by: str | None = None,
        closed_session_notes: str | None = None,
    ) -> PublicMeetingRecord:
        record_id = str(uuid4())
        record = PublicMeetingRecord(
            id=record_id,
            meeting_id=meeting_id,
            title=title,
            visibility=normalize_visibility(visibility),
            posted_agenda=posted_agenda,
            posted_packet=posted_packet,
            approved_minutes=approved_minutes,
            public_comment_enabled=public_comment_enabled,
            plain_language_summary=_normalize_optional_text(plain_language_summary),
            agenda_download_url=f"/public/meetings/{record_id}/agenda.txt",
            packet_download_url=f"/public/meetings/{record_id}/packet.txt",
            minutes_download_url=f"/public/meetings/{record_id}/minutes.txt",
            minutes_adopted_at=_normalize_optional_text(minutes_adopted_at),
            minutes_signed_by=_normalize_optional_text(minutes_signed_by),
            closed_session_notes=closed_session_notes,
        )
        self._records[record.id] = record
        self._records_by_meeting[meeting_id] = record.id
        return record

    def public_calendar(self) -> list[PublicMeetingRecord]:
        return [
            record
            for record in self._records.values()
            if record.visibility == PUBLIC_VISIBILITY
        ]

    def public_detail(self, record_id: str) -> PublicMeetingRecord | None:
        record = self._records.get(record_id)
        if record is None or record.visibility != PUBLIC_VISIBILITY:
            return None
        return record

    def search(self, *, query: str, include_closed: bool = False) -> list[PublicMeetingRecord]:
        normalized_query = normalize_search_query(query)
        results: list[PublicMeetingRecord] = []
        for record in self._records.values():
            if record.visibility != PUBLIC_VISIBILITY and not include_closed:
                continue
            if _record_matches(record, normalized_query, include_closed=include_closed):
                results.append(record)
        return results


class PublicCommentStore:
    """Collect resident comments against public records when comments are enabled."""

    def __init__(self) -> None:
        self._comments: dict[str, PublicCommentRecord] = {}
        self._comments_by_record: dict[str, list[str]] = {}

    def submit(
        self,
        *,
        public_record: PublicMeetingRecord,
        commenter_name: str,
        comment: str,
        submitted_at: str,
    ) -> PublicCommentRecord | None:
        if public_record.visibility != PUBLIC_VISIBILITY or not public_record.public_comment_enabled:
            return None
        name = commenter_name.strip()
        body = comment.strip()
        if not name or not body or len(name) > 255:
            # Same input guard as PublicCommentRepository.submit: blank or
            # schema-overflowing resident input never produces a record.
            return None
        record = PublicCommentRecord(
            id=str(uuid4()),
            public_record_id=public_record.id,
            commenter_name=name,
            comment=body,
            submitted_at=submitted_at,
        )
        self._comments[record.id] = record
        self._comments_by_record.setdefault(public_record.id, []).append(record.id)
        return record

    def list_for_record(self, public_record_id: str) -> list[PublicCommentRecord]:
        return [
            self._comments[comment_id]
            for comment_id in self._comments_by_record.get(public_record_id, [])
        ]

    def list_all(self) -> list[PublicCommentRecord]:
        return list(self._comments.values())


class PublicArchiveRepository:
    """SQLAlchemy-backed public archive on the public_meeting_records table.

    The resident-facing legal record: published meeting records survive an
    API restart. Wiring mirrors MotionVoteRepository: SQLite local demos
    translate the civicclerk schema away; PostgreSQL keeps it. The three
    download URLs are stored so a row round-trips without recomputation.
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
        # Serializes seal+insert+append so concurrent publishes cannot fork
        # the hash chain or leave sealed events for writes that never landed.
        self._chain_lock = threading.Lock()

    def publish(
        self,
        *,
        meeting_id: str,
        title: str,
        visibility: str,
        posted_agenda: str,
        posted_packet: str,
        approved_minutes: str,
        public_comment_enabled: bool = False,
        plain_language_summary: str | None = None,
        minutes_adopted_at: str | None = None,
        minutes_signed_by: str | None = None,
        closed_session_notes: str | None = None,
    ) -> PublicMeetingRecord | None:
        parsed_meeting_id = self._meeting_exists(meeting_id)
        if parsed_meeting_id is None:
            # Match referent semantics across repositories: a meetings parent
            # missing from this database yields None instead of
            # dialect-dependent orphans (SQLite) or raw IntegrityError
            # (PostgreSQL, where migration 0014 enforces the FK).
            return None
        now = datetime.now(UTC)
        record_id = str(uuid4())
        with self._chain_lock:
            event = record_event(
                self.audit_chain.events,
                actor=AuditActor(actor_id="civicclerk", actor_type="system"),
                action="public_archive.record_published",
                subject=AuditSubject(subject_id=record_id, subject_type="public_meeting_record"),
                source_module="civicclerk",
                metadata={
                    "meeting_id": parsed_meeting_id,
                    "visibility": normalize_visibility(visibility),
                },
            )
            values = {
                "id": record_id,
                "meeting_id": parsed_meeting_id,
                "title": title,
                "visibility": normalize_visibility(visibility),
                "posted_agenda": posted_agenda,
                "posted_packet": posted_packet,
                "approved_minutes": approved_minutes,
                "public_comment_enabled": public_comment_enabled,
                "plain_language_summary": _normalize_optional_text(plain_language_summary),
                "agenda_download_url": f"/public/meetings/{record_id}/agenda.txt",
                "packet_download_url": f"/public/meetings/{record_id}/packet.txt",
                "minutes_download_url": f"/public/meetings/{record_id}/minutes.txt",
                "minutes_adopted_at": _normalize_optional_text(minutes_adopted_at),
                "minutes_signed_by": _normalize_optional_text(minutes_signed_by),
                "closed_session_notes": closed_session_notes,
                "created_at": now,
                "updated_at": now,
            }
            with self.engine.begin() as connection:
                values["capture_seq"] = _archive_next_capture_seq(
                    connection, public_meeting_records_table
                )
                connection.execute(public_meeting_records_table.insert().values(**values))
            # Append only after the transaction commits so a failed insert
            # never leaves a phantom sealed event on the chain.
            self.audit_chain.events.append(event)
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(public_meeting_records_table).where(
                    public_meeting_records_table.c.id == record_id
                )
            ).mappings().first()
        return _public_record_row_to_record(row if row is not None else values)

    def public_calendar(self) -> list[PublicMeetingRecord]:
        statement = (
            sa.select(public_meeting_records_table)
            .where(public_meeting_records_table.c.visibility == PUBLIC_VISIBILITY)
            .order_by(public_meeting_records_table.c.capture_seq.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_public_record_row_to_record(row) for row in rows]

    def public_detail(self, record_id: str) -> PublicMeetingRecord | None:
        parsed = _archive_uuid_text_or_none(record_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(public_meeting_records_table).where(
                    public_meeting_records_table.c.id == parsed
                )
            ).mappings().first()
        if row is None:
            return None
        record = _public_record_row_to_record(row)
        if record.visibility != PUBLIC_VISIBILITY:
            return None
        return record

    def search(self, *, query: str, include_closed: bool = False) -> list[PublicMeetingRecord]:
        normalized_query = normalize_search_query(query)
        statement = sa.select(public_meeting_records_table).order_by(
            public_meeting_records_table.c.capture_seq.asc()
        )
        if not include_closed:
            statement = statement.where(
                public_meeting_records_table.c.visibility == PUBLIC_VISIBILITY
            )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        results: list[PublicMeetingRecord] = []
        for row in rows:
            record = _public_record_row_to_record(row)
            if _record_matches(record, normalized_query, include_closed=include_closed):
                results.append(record)
        return results

    def _meeting_exists(self, meeting_id: str) -> str | None:
        parsed = _archive_uuid_text_or_none(meeting_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(meetings_table.c.id).where(meetings_table.c.id == parsed)
            ).first()
        return parsed if row is not None else None


class PublicCommentRepository:
    """SQLAlchemy-backed resident comment intake on the public_comments table.

    The API "comment" field maps to the canonical body column; visibility
    defaults to public because comments are only accepted against public
    records with comment intake enabled (same gating as PublicCommentStore).
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
        # Serializes seal+insert+append so concurrent submissions cannot fork
        # the hash chain or leave sealed events for writes that never landed.
        self._chain_lock = threading.Lock()

    def submit(
        self,
        *,
        public_record: PublicMeetingRecord,
        commenter_name: str,
        comment: str,
        submitted_at: str,
    ) -> PublicCommentRecord | None:
        name = commenter_name.strip()
        body = comment.strip()
        if not name or not body or len(name) > 255:
            # Reject blank or schema-overflowing resident input before the
            # lock/transaction so no chain event or row is ever attempted.
            return None
        row = self._load_record_row(public_record.id)
        if row is None:
            # Match referent semantics across repositories: a parent record
            # missing from this database yields None instead of
            # dialect-dependent orphans (SQLite) or raw IntegrityError
            # (PostgreSQL).
            return None
        if row["visibility"] != PUBLIC_VISIBILITY or not row["public_comment_enabled"]:
            # Gate on the database row, never the caller-supplied snapshot:
            # same semantics as PublicCommentStore's gate, but against truth.
            return None
        now = datetime.now(UTC)
        comment_id = str(uuid4())
        with self._chain_lock:
            event = record_event(
                self.audit_chain.events,
                actor=AuditActor(actor_id=name, actor_type="resident"),
                action="public_archive.comment_received",
                subject=AuditSubject(subject_id=comment_id, subject_type="public_comment"),
                source_module="civicclerk",
                metadata={"public_record_id": str(row["id"])},
            )
            values = {
                "id": comment_id,
                "meeting_id": str(row["meeting_id"]),
                "agenda_item_id": None,
                "public_record_id": str(row["id"]),
                "commenter_name": name,
                "body": body,
                "visibility": PUBLIC_VISIBILITY,
                "status": "RECEIVED",
                "submitted_at": _parse_submitted_at(submitted_at),
                "moderation_notes": None,
                "created_at": now,
                "updated_at": now,
            }
            with self.engine.begin() as connection:
                values["capture_seq"] = _archive_next_capture_seq(
                    connection, public_comments_table
                )
                connection.execute(public_comments_table.insert().values(**values))
            # Append only after the transaction commits so a failed insert
            # never leaves a phantom sealed event on the chain.
            self.audit_chain.events.append(event)
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(public_comments_table).where(public_comments_table.c.id == comment_id)
            ).mappings().first()
        return _comment_row_to_record(row if row is not None else values)

    def list_for_record(self, public_record_id: str) -> list[PublicCommentRecord]:
        parsed = _archive_uuid_text_or_none(public_record_id)
        if parsed is None:
            return []
        statement = (
            sa.select(public_comments_table)
            .where(public_comments_table.c.public_record_id == parsed)
            .order_by(public_comments_table.c.capture_seq.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_comment_row_to_record(row) for row in rows]

    def list_all(self) -> list[PublicCommentRecord]:
        statement = sa.select(public_comments_table).order_by(
            public_comments_table.c.capture_seq.asc()
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_comment_row_to_record(row) for row in rows]

    def _load_record_row(self, public_record_id: str) -> sa.RowMapping | None:
        """Load the gating columns of the parent record from database truth."""

        parsed = _archive_uuid_text_or_none(public_record_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            return connection.execute(
                sa.select(
                    public_meeting_records_table.c.id,
                    public_meeting_records_table.c.meeting_id,
                    public_meeting_records_table.c.visibility,
                    public_meeting_records_table.c.public_comment_enabled,
                ).where(public_meeting_records_table.c.id == parsed)
            ).mappings().first()


def normalize_visibility(visibility: str) -> str:
    return visibility.strip().lower()


def can_view_closed_sessions(roles: set[str] | frozenset[str] | list[str] | tuple[str, ...]) -> bool:
    return roles_grant_access(roles, allowed_roles=PERMITTED_CLOSED_SESSION_ROLES)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _record_matches(
    record: PublicMeetingRecord,
    query: str,
    *,
    include_closed: bool,
) -> bool:
    searchable_text = " ".join(
        [
            record.title,
            record.posted_agenda,
            record.posted_packet,
            record.approved_minutes,
            record.closed_session_notes if include_closed and record.closed_session_notes else "",
        ]
    )
    return search_text_matches_query(text=searchable_text, query=query)


def _archive_next_capture_seq(connection: sa.Connection, table: sa.Table) -> int:
    """Allocate the next monotonic insertion-order sequence for a table.

    Runs inside the insert transaction; callers already hold _chain_lock, so
    MAX+1 cannot race within the single writer process the in-memory audit
    chain requires. Ordering by capture_seq keeps insertion order even when
    rows share a created_at timestamp (the uuid4 id is random and must never
    decide order).
    """

    current = connection.execute(
        sa.select(sa.func.coalesce(sa.func.max(table.c.capture_seq), 0))
    ).scalar_one()
    return int(current) + 1


def _archive_uuid_text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (AttributeError, TypeError, ValueError):
        return None


def _parse_submitted_at(value: str) -> datetime:
    """Normalize API ISO timestamps to timezone-aware UTC before writing.

    SQLite's DateTime(timezone=True) stores naive wall-clock values, so the
    write side pins UTC and the read side restores the offset; the original
    UTC ISO string round-trips byte-identically on both dialects.
    """

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _public_record_row_to_record(row) -> PublicMeetingRecord:
    data = dict(row)
    return PublicMeetingRecord(
        id=str(data["id"]),
        meeting_id=str(data["meeting_id"]),
        title=data["title"],
        visibility=data["visibility"],
        posted_agenda=data["posted_agenda"],
        posted_packet=data["posted_packet"],
        approved_minutes=data["approved_minutes"],
        public_comment_enabled=bool(data["public_comment_enabled"]),
        plain_language_summary=data.get("plain_language_summary"),
        agenda_download_url=data.get("agenda_download_url"),
        packet_download_url=data.get("packet_download_url"),
        minutes_download_url=data.get("minutes_download_url"),
        minutes_adopted_at=data.get("minutes_adopted_at"),
        minutes_signed_by=data.get("minutes_signed_by"),
        closed_session_notes=data.get("closed_session_notes"),
    )


def _comment_row_to_record(row) -> PublicCommentRecord:
    data = dict(row)
    submitted = data.get("submitted_at")
    if isinstance(submitted, datetime):
        if submitted.tzinfo is None:
            # SQLite drops the offset; writes are normalized to UTC, so
            # restoring UTC round-trips the original ISO string.
            submitted = submitted.replace(tzinfo=UTC)
        submitted_text = submitted.isoformat()
    else:
        submitted_text = str(submitted) if submitted else ""
    return PublicCommentRecord(
        id=str(data["id"]),
        public_record_id=str(data["public_record_id"]) if data.get("public_record_id") else "",
        commenter_name=data["commenter_name"],
        comment=data["body"],
        submitted_at=submitted_text,
        status=data.get("status") or "RECEIVED",
    )


__all__ = [
    "CLOSED_SESSION_VISIBILITY",
    "PERMITTED_CLOSED_SESSION_ROLES",
    "PUBLIC_VISIBILITY",
    "PublicArchiveRepository",
    "PublicArchiveStore",
    "PublicCommentRecord",
    "PublicCommentRepository",
    "PublicCommentStore",
    "PublicMeetingRecord",
    "can_view_closed_sessions",
    "normalize_visibility",
]
