"""Meeting lifecycle enforcement for CivicClerk.

Milestone 4 establishes the meeting state machine and audit contract. Packet
assembly, notice compliance, minutes drafting, and archival workflow remain
later milestones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

MEETING_LIFECYCLE = (
    "SCHEDULED",
    "NOTICED",
    "PACKET_POSTED",
    "IN_PROGRESS",
    "RECESSED",
    "ADJOURNED",
    "TRANSCRIPT_READY",
    "MINUTES_DRAFTED",
    "MINUTES_POSTED",
    "MINUTES_ADOPTED",
    "MINUTES_SIGNED",
    "ARCHIVED",
)

CANCELLED_STATUS = "CANCELLED"
VALID_TRANSITIONS = dict(zip(MEETING_LIFECYCLE[:-1], MEETING_LIFECYCLE[1:], strict=True))
SPECIAL_TRANSITIONS = {
    ("RECESSED", "IN_PROGRESS"),
    ("SCHEDULED", CANCELLED_STATUS),
    ("NOTICED", CANCELLED_STATUS),
}
KNOWN_STATUSES = (*MEETING_LIFECYCLE, CANCELLED_STATUS)
EMERGENCY_NOTICE_TYPES = {"emergency", "special"}
CLOSED_SESSION_TYPES = {"closed_session", "executive"}
KNOWN_MEETING_TYPES = {"regular", *EMERGENCY_NOTICE_TYPES, *CLOSED_SESSION_TYPES}

metadata = sa.MetaData()

meeting_records = sa.Table(
    "meeting_records",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("meeting_type", sa.String(80), nullable=False),
    sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("audit_entries", sa.JSON(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)


@dataclass(frozen=True)
class TransitionResult:
    allowed: bool
    http_status: int
    message: str
    audit_entry: dict[str, str]


@dataclass
class MeetingRecord:
    id: str
    title: str
    meeting_type: str
    scheduled_start: datetime | None = None
    status: str = "SCHEDULED"
    audit_entries: list[dict[str, str]] = field(default_factory=list)

    def public_dict(self) -> dict[str, str | None]:
        payload = {
            "id": self.id,
            "title": self.title,
            "meeting_type": self.meeting_type,
            "status": self.status,
        }
        if self.scheduled_start is not None:
            payload["scheduled_start"] = self.scheduled_start.isoformat()
        return payload


class MeetingStore:
    """Meeting store with optional SQLAlchemy persistence."""

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        self._meetings: dict[str, MeetingRecord] = {}
        self.engine: Engine | None = None
        if db_url is not None or engine is not None:
            base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
            if base_engine.dialect.name == "sqlite":
                self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
            else:
                self.engine = base_engine
                with self.engine.begin() as connection:
                    connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
            metadata.create_all(self.engine)

    def create(
        self,
        *,
        title: str,
        meeting_type: str,
        scheduled_start: datetime | None = None,
    ) -> MeetingRecord:
        meeting = MeetingRecord(
            id=str(uuid4()),
            title=title,
            meeting_type=normalize_meeting_type(meeting_type),
            scheduled_start=_normalize_scheduled_start(scheduled_start),
        )
        if self.engine is not None:
            now = datetime.now(UTC)
            with self.engine.begin() as connection:
                connection.execute(
                    meeting_records.insert().values(
                        id=meeting.id,
                        title=meeting.title,
                        meeting_type=meeting.meeting_type,
                        scheduled_start=meeting.scheduled_start,
                        status=meeting.status,
                        audit_entries=meeting.audit_entries,
                        created_at=now,
                        updated_at=now,
                    )
                )
        self._meetings[meeting.id] = meeting
        return meeting

    def get(self, meeting_id: str) -> MeetingRecord | None:
        if self.engine is not None:
            with self.engine.begin() as connection:
                row = connection.execute(
                    sa.select(meeting_records).where(meeting_records.c.id == meeting_id)
                ).mappings().first()
            return _row_to_meeting(row) if row is not None else None
        return self._meetings.get(meeting_id)

    def transition(
        self,
        *,
        meeting_id: str,
        to_status: str,
        actor: str,
        statutory_basis: str | None,
    ) -> TransitionResult | None:
        meeting = self.get(meeting_id)
        if meeting is None:
            return None
        result = validate_meeting_transition(
            meeting_id=meeting_id,
            from_status=meeting.status,
            to_status=to_status,
            actor=actor,
            meeting_type=meeting.meeting_type,
            statutory_basis=statutory_basis,
        )
        meeting.audit_entries.append(result.audit_entry)
        if result.allowed:
            meeting.status = to_status
        if self.engine is not None:
            with self.engine.begin() as connection:
                connection.execute(
                    meeting_records.update()
                    .where(meeting_records.c.id == meeting_id)
                    .values(
                        status=meeting.status,
                        audit_entries=meeting.audit_entries,
                        updated_at=datetime.now(UTC),
                    )
                )
        else:
            self._meetings[meeting_id] = meeting
        return result


def validate_meeting_transition(
    *,
    meeting_id: str,
    from_status: str,
    to_status: str,
    actor: str,
    meeting_type: str,
    statutory_basis: str | None,
) -> TransitionResult:
    """Validate one meeting lifecycle transition and produce an audit entry."""
    normalized_meeting_type = normalize_meeting_type(meeting_type)
    base_entry = {
        "meeting_id": meeting_id,
        "actor": actor,
        "from_status": from_status,
        "to_status": to_status,
        "meeting_type": normalized_meeting_type,
    }
    if statutory_basis:
        base_entry["statutory_basis"] = statutory_basis

    if from_status not in KNOWN_STATUSES:
        return _rejected(
            base_entry,
            422,
            f"Unknown current meeting status {from_status}. Use one of {', '.join(KNOWN_STATUSES)}.",
            "unknown current meeting status",
        )

    if to_status not in KNOWN_STATUSES:
        return _rejected(
            base_entry,
            422,
            f"Unknown requested meeting status {to_status}. Use one of {', '.join(KNOWN_STATUSES)}.",
            "unknown requested meeting status",
        )

    if normalized_meeting_type in EMERGENCY_NOTICE_TYPES and from_status == "SCHEDULED" and to_status == "NOTICED":
        if not statutory_basis:
            return _rejected(
                base_entry,
                422,
                f"{normalized_meeting_type.title()} meetings require a statutory basis before notice is posted.",
                "missing statutory basis for emergency or special meeting notice",
            )

    if normalized_meeting_type in CLOSED_SESSION_TYPES and from_status == "PACKET_POSTED" and to_status == "IN_PROGRESS":
        if not statutory_basis:
            return _rejected(
                base_entry,
                422,
                "Closed or executive sessions require a statutory basis before moving in progress.",
                "missing statutory basis for closed session",
            )

    if VALID_TRANSITIONS.get(from_status) == to_status or (from_status, to_status) in SPECIAL_TRANSITIONS:
        return TransitionResult(
            allowed=True,
            http_status=200,
            message="transition allowed",
            audit_entry={
                **base_entry,
                "outcome": "allowed",
                "reason": "transition allowed",
            },
        )

    next_status = VALID_TRANSITIONS.get(from_status, "no further status")
    return _rejected(
        base_entry,
        409,
        (
            "Invalid meeting lifecycle transition. The canonical next status "
            f"from {from_status} is {next_status}. Next valid status is {next_status}."
        ),
        "invalid meeting lifecycle transition",
    )


def normalize_meeting_type(meeting_type: str) -> str:
    """Normalize user-provided meeting type labels before compliance checks."""
    return meeting_type.strip().lower()


def _rejected(
    base_entry: dict[str, str],
    http_status: int,
    message: str,
    reason: str,
) -> TransitionResult:
    return TransitionResult(
        allowed=False,
        http_status=http_status,
        message=message,
        audit_entry={
            **base_entry,
            "outcome": "rejected",
            "reason": reason,
        },
    )


def _row_to_meeting(row) -> MeetingRecord:
    data = dict(row)
    scheduled_start = _normalize_scheduled_start(data["scheduled_start"])
    return MeetingRecord(
        id=data["id"],
        title=data["title"],
        meeting_type=data["meeting_type"],
        scheduled_start=scheduled_start,
        status=data["status"],
        audit_entries=list(data["audit_entries"]),
    )


def _normalize_scheduled_start(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "CANCELLED_STATUS",
    "KNOWN_STATUSES",
    "KNOWN_MEETING_TYPES",
    "MEETING_LIFECYCLE",
    "SPECIAL_TRANSITIONS",
    "VALID_TRANSITIONS",
    "MeetingRecord",
    "MeetingStore",
    "TransitionResult",
    "meeting_records",
    "validate_meeting_transition",
]
