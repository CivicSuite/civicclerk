"""Motion, vote, and action-item capture helpers for CivicMeetings."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiccore.audit import AuditActor, AuditHashChain, AuditSubject, record_event


@dataclass(frozen=True)
class MotionRecord:
    id: str
    meeting_id: str
    text: str
    actor: str
    agenda_item_id: str | None = None
    seconded_by: str | None = None
    correction_of_id: str | None = None
    correction_reason: str | None = None
    captured: bool = True

    def public_dict(self) -> dict[str, str | bool | None]:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "agenda_item_id": self.agenda_item_id,
            "text": self.text,
            "actor": self.actor,
            "seconded_by": self.seconded_by,
            "correction_of_id": self.correction_of_id,
            "correction_reason": self.correction_reason,
            "captured": self.captured,
        }


@dataclass(frozen=True)
class VoteRecord:
    id: str
    motion_id: str
    voter_name: str
    vote: str
    actor: str
    correction_of_id: str | None = None
    correction_reason: str | None = None
    captured: bool = True

    def public_dict(self) -> dict[str, str | bool | None]:
        return {
            "id": self.id,
            "motion_id": self.motion_id,
            "voter_name": self.voter_name,
            "vote": self.vote,
            "actor": self.actor,
            "correction_of_id": self.correction_of_id,
            "correction_reason": self.correction_reason,
            "captured": self.captured,
        }


@dataclass(frozen=True)
class ActionItemRecord:
    id: str
    meeting_id: str
    description: str
    actor: str
    assigned_to: str | None = None
    source_motion_id: str | None = None
    status: str = "OPEN"

    def public_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "source_motion_id": self.source_motion_id,
            "status": self.status,
            "actor": self.actor,
        }


@dataclass(frozen=True)
class MeetingOutcomeSummary:
    meeting_id: str
    motion_id: str
    text: str
    actor: str
    status: str
    vote_count: int
    action_item_count: int


metadata = sa.MetaData()

motions_table = sa.Table(
    "motions",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("agenda_item_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("seconded_by", sa.String(255), nullable=True),
    sa.Column("captured_by", sa.String(255), nullable=True),
    sa.Column("correction_of_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("correction_reason", sa.Text(), nullable=True),
    sa.Column("immutable_hash", sa.String(128), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

votes_table = sa.Table(
    "votes",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("motion_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("voter_name", sa.String(255), nullable=False),
    sa.Column("vote", sa.String(50), nullable=False),
    sa.Column("actor", sa.String(255), nullable=True),
    sa.Column("correction_of_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("correction_reason", sa.Text(), nullable=True),
    sa.Column("immutable_hash", sa.String(128), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

action_items_table = sa.Table(
    "action_items",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("description", sa.Text(), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("assigned_to", sa.String(255), nullable=True),
    sa.Column("source_motion_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("actor", sa.String(255), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)


class MotionVoteStore:
    """In-memory capture store until database-backed workflow persistence lands."""

    def __init__(self) -> None:
        self._motions: dict[str, MotionRecord] = {}
        self._motions_by_meeting: dict[str, list[str]] = {}
        self._votes: dict[str, VoteRecord] = {}
        self._votes_by_motion: dict[str, list[str]] = {}
        self._action_items: dict[str, ActionItemRecord] = {}
        self._action_items_by_meeting: dict[str, list[str]] = {}

    def capture_motion(
        self,
        *,
        meeting_id: str,
        text: str,
        actor: str,
        agenda_item_id: str | None = None,
        seconded_by: str | None = None,
        correction_of_id: str | None = None,
        correction_reason: str | None = None,
    ) -> MotionRecord:
        motion = MotionRecord(
            id=str(uuid4()),
            meeting_id=meeting_id,
            agenda_item_id=agenda_item_id,
            text=text,
            actor=actor,
            seconded_by=_normalize_optional_text(seconded_by),
            correction_of_id=correction_of_id,
            correction_reason=correction_reason,
        )
        self._motions[motion.id] = motion
        self._motions_by_meeting.setdefault(meeting_id, []).append(motion.id)
        return motion

    def get_motion(self, motion_id: str) -> MotionRecord | None:
        return self._motions.get(motion_id)

    def list_motions(self, meeting_id: str) -> list[MotionRecord]:
        return [
            self._motions[motion_id]
            for motion_id in self._motions_by_meeting.get(meeting_id, [])
        ]

    def correct_motion(
        self,
        *,
        original_motion_id: str,
        text: str,
        actor: str,
        reason: str,
    ) -> MotionRecord | None:
        original = self.get_motion(original_motion_id)
        if original is None:
            return None
        return self.capture_motion(
            meeting_id=original.meeting_id,
            agenda_item_id=original.agenda_item_id,
            text=text,
            actor=actor,
            seconded_by=original.seconded_by,
            correction_of_id=original.id,
            correction_reason=reason,
        )

    def capture_vote(
        self,
        *,
        motion_id: str,
        voter_name: str,
        vote: str,
        actor: str,
        correction_of_id: str | None = None,
        correction_reason: str | None = None,
    ) -> VoteRecord:
        record = VoteRecord(
            id=str(uuid4()),
            motion_id=motion_id,
            voter_name=voter_name,
            vote=vote.strip().lower(),
            actor=actor,
            correction_of_id=correction_of_id,
            correction_reason=correction_reason,
        )
        self._votes[record.id] = record
        self._votes_by_motion.setdefault(motion_id, []).append(record.id)
        return record

    def get_vote(self, vote_id: str) -> VoteRecord | None:
        return self._votes.get(vote_id)

    def list_votes(self, motion_id: str) -> list[VoteRecord]:
        return [self._votes[vote_id] for vote_id in self._votes_by_motion.get(motion_id, [])]

    def correct_vote(
        self,
        *,
        original_vote_id: str,
        vote: str,
        actor: str,
        reason: str,
    ) -> VoteRecord | None:
        original = self.get_vote(original_vote_id)
        if original is None:
            return None
        return self.capture_vote(
            motion_id=original.motion_id,
            voter_name=original.voter_name,
            vote=vote,
            actor=actor,
            correction_of_id=original.id,
            correction_reason=reason,
        )

    def create_action_item(
        self,
        *,
        meeting_id: str,
        description: str,
        actor: str,
        assigned_to: str | None = None,
        source_motion_id: str | None = None,
    ) -> ActionItemRecord:
        action_item = ActionItemRecord(
            id=str(uuid4()),
            meeting_id=meeting_id,
            description=description,
            assigned_to=assigned_to,
            source_motion_id=source_motion_id,
            actor=actor,
        )
        self._action_items[action_item.id] = action_item
        self._action_items_by_meeting.setdefault(meeting_id, []).append(action_item.id)
        return action_item

    def list_action_items(self, meeting_id: str) -> list[ActionItemRecord]:
        return [
            self._action_items[action_item_id]
            for action_item_id in self._action_items_by_meeting.get(meeting_id, [])
        ]

    def list_recent_outcomes(self, *, limit: int = 5) -> list[MeetingOutcomeSummary]:
        """Return recent motion-centered outcome summaries for the staff dashboard."""

        summaries: list[MeetingOutcomeSummary] = []
        for motion in reversed(list(self._motions.values())):
            action_item_count = sum(
                1
                for action_item_id in self._action_items_by_meeting.get(motion.meeting_id, [])
                if self._action_items[action_item_id].source_motion_id == motion.id
            )
            summaries.append(
                MeetingOutcomeSummary(
                    meeting_id=motion.meeting_id,
                    motion_id=motion.id,
                    text=motion.text,
                    actor=motion.actor,
                    status="APPENDED" if motion.correction_of_id else "CAPTURED",
                    vote_count=len(self._votes_by_motion.get(motion.id, [])),
                    action_item_count=action_item_count,
                )
            )
            if len(summaries) >= limit:
                break
        return summaries


class MotionVoteRepository:
    """SQLAlchemy-backed motion, vote, and action-item capture store.

    Persists the legal record onto the canonical civicclerk.motions, votes,
    and action_items tables so captured outcomes survive an API restart.
    Wiring mirrors AgendaIntakeRepository: SQLite local demos translate the
    civicclerk schema away; PostgreSQL keeps it. Corrections stay append-only
    insert operations; rows are never updated or deleted.
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
        # Serializes seal+insert+append so concurrent captures cannot fork the
        # hash chain or leave sealed events for writes that never landed.
        self._chain_lock = threading.Lock()

    def capture_motion(
        self,
        *,
        meeting_id: str,
        text: str,
        actor: str,
        agenda_item_id: str | None = None,
        seconded_by: str | None = None,
        correction_of_id: str | None = None,
        correction_reason: str | None = None,
    ) -> MotionRecord:
        now = datetime.now(UTC)
        motion_id = str(uuid4())
        with self._chain_lock:
            event = record_event(
                self.audit_chain.events,
                actor=AuditActor(actor_id=actor, actor_type="clerk"),
                action="motion_vote.motion_captured",
                subject=AuditSubject(subject_id=motion_id, subject_type="motion"),
                source_module="civicclerk",
                metadata={
                    "meeting_id": meeting_id,
                    "correction_of_id": correction_of_id,
                },
            )
            values = {
                "id": motion_id,
                "meeting_id": meeting_id,
                "agenda_item_id": _uuid_text_or_none(agenda_item_id),
                "text": text,
                "seconded_by": _normalize_optional_text(seconded_by),
                "captured_by": actor,
                "correction_of_id": correction_of_id,
                "correction_reason": correction_reason,
                "immutable_hash": event.current_hash or "",
                "created_at": now,
                "updated_at": now,
            }
            with self.engine.begin() as connection:
                values["capture_seq"] = _next_capture_seq(connection, motions_table)
                connection.execute(motions_table.insert().values(**values))
            # Append only after the transaction commits so a failed insert
            # never leaves a phantom sealed event on the chain.
            self.audit_chain.events.append(event)
        return self.get_motion(motion_id) or _motion_row_to_record(values)

    def get_motion(self, motion_id: str) -> MotionRecord | None:
        parsed = _uuid_text_or_none(motion_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(motions_table).where(motions_table.c.id == parsed)
            ).mappings().first()
        return _motion_row_to_record(row) if row is not None else None

    def list_motions(self, meeting_id: str) -> list[MotionRecord]:
        parsed = _uuid_text_or_none(meeting_id)
        if parsed is None:
            return []
        statement = (
            sa.select(motions_table)
            .where(motions_table.c.meeting_id == parsed)
            .order_by(motions_table.c.capture_seq.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_motion_row_to_record(row) for row in rows]

    def correct_motion(
        self,
        *,
        original_motion_id: str,
        text: str,
        actor: str,
        reason: str,
    ) -> MotionRecord | None:
        original = self.get_motion(original_motion_id)
        if original is None:
            return None
        return self.capture_motion(
            meeting_id=original.meeting_id,
            agenda_item_id=original.agenda_item_id,
            text=text,
            actor=actor,
            seconded_by=original.seconded_by,
            correction_of_id=original.id,
            correction_reason=reason,
        )

    def capture_vote(
        self,
        *,
        motion_id: str,
        voter_name: str,
        vote: str,
        actor: str,
        correction_of_id: str | None = None,
        correction_reason: str | None = None,
    ) -> VoteRecord | None:
        if self.get_motion(motion_id) is None:
            # Match correct_* semantics: missing referents yield None instead
            # of dialect-dependent orphans (SQLite) or raw IntegrityError
            # (PostgreSQL).
            return None
        now = datetime.now(UTC)
        vote_id = str(uuid4())
        with self._chain_lock:
            event = record_event(
                self.audit_chain.events,
                actor=AuditActor(actor_id=actor, actor_type="clerk"),
                action="motion_vote.vote_captured",
                subject=AuditSubject(subject_id=vote_id, subject_type="vote"),
                source_module="civicclerk",
                metadata={
                    "motion_id": motion_id,
                    "correction_of_id": correction_of_id,
                },
            )
            values = {
                "id": vote_id,
                "motion_id": motion_id,
                "voter_name": voter_name,
                "vote": vote.strip().lower(),
                "actor": actor,
                "correction_of_id": correction_of_id,
                "correction_reason": correction_reason,
                "immutable_hash": event.current_hash or "",
                "created_at": now,
                "updated_at": now,
            }
            with self.engine.begin() as connection:
                values["capture_seq"] = _next_capture_seq(connection, votes_table)
                connection.execute(votes_table.insert().values(**values))
            # Append only after the transaction commits so a failed insert
            # never leaves a phantom sealed event on the chain.
            self.audit_chain.events.append(event)
        return self.get_vote(vote_id) or _vote_row_to_record(values)

    def get_vote(self, vote_id: str) -> VoteRecord | None:
        parsed = _uuid_text_or_none(vote_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(votes_table).where(votes_table.c.id == parsed)
            ).mappings().first()
        return _vote_row_to_record(row) if row is not None else None

    def list_votes(self, motion_id: str) -> list[VoteRecord]:
        parsed = _uuid_text_or_none(motion_id)
        if parsed is None:
            return []
        statement = (
            sa.select(votes_table)
            .where(votes_table.c.motion_id == parsed)
            .order_by(votes_table.c.capture_seq.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_vote_row_to_record(row) for row in rows]

    def correct_vote(
        self,
        *,
        original_vote_id: str,
        vote: str,
        actor: str,
        reason: str,
    ) -> VoteRecord | None:
        original = self.get_vote(original_vote_id)
        if original is None:
            return None
        return self.capture_vote(
            motion_id=original.motion_id,
            voter_name=original.voter_name,
            vote=vote,
            actor=actor,
            correction_of_id=original.id,
            correction_reason=reason,
        )

    def create_action_item(
        self,
        *,
        meeting_id: str,
        description: str,
        actor: str,
        assigned_to: str | None = None,
        source_motion_id: str | None = None,
    ) -> ActionItemRecord | None:
        if source_motion_id is not None and self.get_motion(source_motion_id) is None:
            # Match correct_* semantics: missing referents yield None instead
            # of dialect-dependent orphans (SQLite) or raw IntegrityError
            # (PostgreSQL).
            return None
        now = datetime.now(UTC)
        action_item_id = str(uuid4())
        with self._chain_lock:
            event = record_event(
                self.audit_chain.events,
                actor=AuditActor(actor_id=actor, actor_type="clerk"),
                action="motion_vote.action_item_created",
                subject=AuditSubject(subject_id=action_item_id, subject_type="action_item"),
                source_module="civicclerk",
                metadata={
                    "meeting_id": meeting_id,
                    "source_motion_id": source_motion_id,
                },
            )
            values = {
                "id": action_item_id,
                "meeting_id": meeting_id,
                "description": description,
                "status": "OPEN",
                "assigned_to": assigned_to,
                "source_motion_id": source_motion_id,
                "actor": actor,
                "created_at": now,
                "updated_at": now,
            }
            with self.engine.begin() as connection:
                values["capture_seq"] = _next_capture_seq(connection, action_items_table)
                connection.execute(action_items_table.insert().values(**values))
            # action_items has no immutable_hash column; the chain still records
            # the write, appended only after the transaction commits so a failed
            # insert never leaves a phantom sealed event.
            self.audit_chain.events.append(event)
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(action_items_table).where(action_items_table.c.id == action_item_id)
            ).mappings().first()
        return _action_item_row_to_record(row if row is not None else values)

    def list_action_items(self, meeting_id: str) -> list[ActionItemRecord]:
        parsed = _uuid_text_or_none(meeting_id)
        if parsed is None:
            return []
        statement = (
            sa.select(action_items_table)
            .where(action_items_table.c.meeting_id == parsed)
            .order_by(action_items_table.c.capture_seq.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_action_item_row_to_record(row) for row in rows]

    def list_recent_outcomes(self, *, limit: int = 5) -> list[MeetingOutcomeSummary]:
        """Return recent motion-centered outcome summaries for the staff dashboard."""

        summaries: list[MeetingOutcomeSummary] = []
        with self.engine.begin() as connection:
            motion_rows = connection.execute(
                sa.select(motions_table)
                .order_by(motions_table.c.capture_seq.desc())
                .limit(limit)
            ).mappings().all()
            for row in motion_rows:
                vote_count = connection.execute(
                    sa.select(sa.func.count())
                    .select_from(votes_table)
                    .where(votes_table.c.motion_id == row["id"])
                ).scalar_one()
                action_item_count = connection.execute(
                    sa.select(sa.func.count())
                    .select_from(action_items_table)
                    .where(action_items_table.c.source_motion_id == row["id"])
                ).scalar_one()
                record = _motion_row_to_record(row)
                summaries.append(
                    MeetingOutcomeSummary(
                        meeting_id=record.meeting_id,
                        motion_id=record.id,
                        text=record.text,
                        actor=record.actor,
                        status="APPENDED" if record.correction_of_id else "CAPTURED",
                        vote_count=int(vote_count),
                        action_item_count=int(action_item_count),
                    )
                )
        return summaries


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _next_capture_seq(connection: sa.Connection, table: sa.Table) -> int:
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


def _uuid_text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (AttributeError, TypeError, ValueError):
        return None


def _motion_row_to_record(row) -> MotionRecord:
    data = dict(row)
    return MotionRecord(
        id=str(data["id"]),
        meeting_id=str(data["meeting_id"]),
        agenda_item_id=str(data["agenda_item_id"]) if data.get("agenda_item_id") else None,
        text=data["text"],
        actor=data.get("captured_by") or "",
        seconded_by=data.get("seconded_by"),
        correction_of_id=str(data["correction_of_id"]) if data.get("correction_of_id") else None,
        correction_reason=data.get("correction_reason"),
    )


def _vote_row_to_record(row) -> VoteRecord:
    data = dict(row)
    return VoteRecord(
        id=str(data["id"]),
        motion_id=str(data["motion_id"]),
        voter_name=data["voter_name"],
        vote=data["vote"],
        actor=data.get("actor") or "",
        correction_of_id=str(data["correction_of_id"]) if data.get("correction_of_id") else None,
        correction_reason=data.get("correction_reason"),
    )


def _action_item_row_to_record(row) -> ActionItemRecord:
    data = dict(row)
    return ActionItemRecord(
        id=str(data["id"]),
        meeting_id=str(data["meeting_id"]),
        description=data["description"],
        actor=data.get("actor") or "",
        assigned_to=data.get("assigned_to"),
        source_motion_id=str(data["source_motion_id"]) if data.get("source_motion_id") else None,
        status=data.get("status") or "OPEN",
    )


__all__ = [
    "ActionItemRecord",
    "MeetingOutcomeSummary",
    "MotionRecord",
    "MotionVoteRepository",
    "MotionVoteStore",
    "VoteRecord",
]
