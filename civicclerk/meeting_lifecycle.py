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
    sa.Column("meeting_body_id", sa.String(64), nullable=True),
    sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
    sa.Column("location", sa.String(255), nullable=True),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("audit_entries", sa.JSON(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

EDITABLE_MEETING_STATUSES = {"SCHEDULED", "NOTICED", "PACKET_POSTED"}


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
    meeting_body_id: str | None = None
    location: str | None = None
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
        if self.meeting_body_id:
            payload["meeting_body_id"] = self.meeting_body_id
        if self.location:
            payload["location"] = self.location
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
        meeting_body_id: str | None = None,
        location: str | None = None,
    ) -> MeetingRecord:
        meeting = MeetingRecord(
            id=str(uuid4()),
            title=title,
            meeting_type=normalize_meeting_type(meeting_type),
            scheduled_start=_normalize_scheduled_start(scheduled_start),
            meeting_body_id=_normalize_optional_text(meeting_body_id),
            location=_normalize_optional_text(location),
        )
        if self.engine is not None:
            now = datetime.now(UTC)
            with self.engine.begin() as connection:
                connection.execute(
                    meeting_records.insert().values(
                        id=meeting.id,
                        title=meeting.title,
                        meeting_type=meeting.meeting_type,
                        meeting_body_id=meeting.meeting_body_id,
                        scheduled_start=meeting.scheduled_start,
                        location=meeting.location,
                        status=meeting.status,
                        audit_entries=meeting.audit_entries,
                        created_at=now,
                        updated_at=now,
                    )
                )
        self._meetings[meeting.id] = meeting
        return meeting

    def update_schedule(
        self,
        *,
        meeting_id: str,
        actor: str,
        title: str | None = None,
        meeting_type: str | None = None,
        scheduled_start: datetime | None = None,
        meeting_body_id: str | None = None,
        location: str | None = None,
    ) -> MeetingRecord | None:
        meeting = self.get(meeting_id)
        if meeting is None:
            return None
        if meeting.status not in EDITABLE_MEETING_STATUSES:
            raise MeetingScheduleUpdateError(
                "Meeting schedule is locked after the public meeting is in progress.",
                (
                    "Use lifecycle corrections, minutes notes, or a new replacement meeting rather than "
                    f"editing schedule fields while the meeting is {meeting.status}."
                ),
            )

        changes: dict[str, str | None] = {}
        if title is not None and title != meeting.title:
            changes["title"] = title
            meeting.title = title
        if meeting_type is not None:
            normalized_type = normalize_meeting_type(meeting_type)
            if normalized_type != meeting.meeting_type:
                changes["meeting_type"] = normalized_type
                meeting.meeting_type = normalized_type
        normalized_start = _normalize_scheduled_start(scheduled_start)
        if scheduled_start is not None and normalized_start != meeting.scheduled_start:
            changes["scheduled_start"] = normalized_start.isoformat() if normalized_start else None
            meeting.scheduled_start = normalized_start
        normalized_body_id = _normalize_optional_text(meeting_body_id)
        if meeting_body_id is not None and normalized_body_id != meeting.meeting_body_id:
            changes["meeting_body_id"] = normalized_body_id
            meeting.meeting_body_id = normalized_body_id
        normalized_location = _normalize_optional_text(location)
        if location is not None and normalized_location != meeting.location:
            changes["location"] = normalized_location
            meeting.location = normalized_location

        if changes:
            meeting.audit_entries.append(
                {
                    "meeting_id": meeting_id,
                    "actor": actor,
                    "from_status": meeting.status,
                    "to_status": meeting.status,
                    "outcome": "allowed",
                    "reason": "meeting schedule updated",
                    "changed_fields": ",".join(sorted(changes)),
                }
            )
        if self.engine is not None:
            with self.engine.begin() as connection:
                connection.execute(
                    meeting_records.update()
                    .where(meeting_records.c.id == meeting_id)
                    .values(
                        title=meeting.title,
                        meeting_type=meeting.meeting_type,
                        meeting_body_id=meeting.meeting_body_id,
                        scheduled_start=meeting.scheduled_start,
                        location=meeting.location,
                        audit_entries=meeting.audit_entries,
                        updated_at=datetime.now(UTC),
                    )
                )
        else:
            self._meetings[meeting_id] = meeting
        return meeting

    def get(self, meeting_id: str) -> MeetingRecord | None:
        if self.engine is not None:
            with self.engine.begin() as connection:
                row = connection.execute(
                    sa.select(meeting_records).where(meeting_records.c.id == meeting_id)
                ).mappings().first()
            return _row_to_meeting(row) if row is not None else None
        return self._meetings.get(meeting_id)

    def list(self) -> list[MeetingRecord]:
        """Return meetings in calendar-friendly order."""
        if self.engine is not None:
            with self.engine.begin() as connection:
                rows = connection.execute(
                    sa.select(meeting_records).order_by(
                        meeting_records.c.scheduled_start.is_(None),
                        meeting_records.c.scheduled_start,
                        meeting_records.c.title,
                    )
                ).mappings().all()
            return [_row_to_meeting(row) for row in rows]
        return sorted(
            self._meetings.values(),
            key=lambda meeting: (
                meeting.scheduled_start is None,
                meeting.scheduled_start or datetime.max.replace(tzinfo=UTC),
                meeting.title,
            ),
        )

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
        meeting_body_id=data.get("meeting_body_id"),
        location=data.get("location"),
        status=data["status"],
        audit_entries=list(data["audit_entries"]),
    )


def _normalize_scheduled_start(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class MeetingScheduleUpdateError(ValueError):
    """Raised when staff tries to edit schedule fields after the legal lock point."""

    def __init__(self, message: str, fix: str) -> None:
        super().__init__(message)
        self.message = message
        self.fix = fix


__all__ = [
    "CANCELLED_STATUS",
    "KNOWN_STATUSES",
    "KNOWN_MEETING_TYPES",
    "MEETING_LIFECYCLE",
    "SPECIAL_TRANSITIONS",
    "VALID_TRANSITIONS",
    "MeetingRecord",
    "MeetingScheduleUpdateError",
    "MeetingStore",
    "TransitionResult",
    "meeting_records",
    "validate_meeting_transition",
]
