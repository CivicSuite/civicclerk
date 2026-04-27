"""Meeting lifecycle enforcement for CivicClerk.

Milestone 4 establishes the meeting state machine and audit contract. Packet
assembly, notice compliance, minutes drafting, and archival workflow remain
later milestones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


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
    status: str = "SCHEDULED"
    audit_entries: list[dict[str, str]] = field(default_factory=list)

    def public_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "meeting_type": self.meeting_type,
            "status": self.status,
        }


class MeetingStore:
    """Small in-memory store used until DB-backed workflow routes land."""

    def __init__(self) -> None:
        self._meetings: dict[str, MeetingRecord] = {}

    def create(self, *, title: str, meeting_type: str) -> MeetingRecord:
        meeting = MeetingRecord(
            id=str(uuid4()),
            title=title,
            meeting_type=meeting_type,
        )
        self._meetings[meeting.id] = meeting
        return meeting

    def get(self, meeting_id: str) -> MeetingRecord | None:
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
    base_entry = {
        "meeting_id": meeting_id,
        "actor": actor,
        "from_status": from_status,
        "to_status": to_status,
        "meeting_type": meeting_type,
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

    if meeting_type in EMERGENCY_NOTICE_TYPES and from_status == "SCHEDULED" and to_status == "NOTICED":
        if not statutory_basis:
            return _rejected(
                base_entry,
                422,
                f"{meeting_type.title()} meetings require a statutory basis before notice is posted.",
                "missing statutory basis for emergency or special meeting notice",
            )

    if meeting_type in CLOSED_SESSION_TYPES and from_status == "PACKET_POSTED" and to_status == "IN_PROGRESS":
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


__all__ = [
    "CANCELLED_STATUS",
    "KNOWN_STATUSES",
    "MEETING_LIFECYCLE",
    "SPECIAL_TRANSITIONS",
    "VALID_TRANSITIONS",
    "MeetingRecord",
    "MeetingStore",
    "TransitionResult",
    "validate_meeting_transition",
]
