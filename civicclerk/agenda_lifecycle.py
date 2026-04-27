"""Agenda item lifecycle enforcement for CivicClerk.

Milestone 3 keeps storage intentionally simple while establishing the
non-negotiable state machine contract. Database-backed persistence lands after
the API behavior and audit semantics are locked by tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


AGENDA_ITEM_LIFECYCLE = (
    "DRAFTED",
    "SUBMITTED",
    "DEPT_APPROVED",
    "LEGAL_REVIEWED",
    "CLERK_ACCEPTED",
    "ON_AGENDA",
    "IN_PACKET",
    "POSTED",
    "HEARD",
    "DISPOSED",
    "ARCHIVED",
)

VALID_TRANSITIONS = dict(zip(AGENDA_ITEM_LIFECYCLE[:-1], AGENDA_ITEM_LIFECYCLE[1:], strict=True))


@dataclass(frozen=True)
class TransitionResult:
    allowed: bool
    http_status: int
    message: str
    audit_entry: dict[str, str]


@dataclass
class AgendaItemRecord:
    id: str
    title: str
    department_name: str
    status: str = "DRAFTED"
    audit_entries: list[dict[str, str]] = field(default_factory=list)

    def public_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "department_name": self.department_name,
            "status": self.status,
        }


class AgendaItemStore:
    """Small in-memory store used until Milestone 3 grows DB-backed routes."""

    def __init__(self) -> None:
        self._items: dict[str, AgendaItemRecord] = {}

    def create(self, *, title: str, department_name: str) -> AgendaItemRecord:
        item = AgendaItemRecord(
            id=str(uuid4()),
            title=title,
            department_name=department_name,
        )
        self._items[item.id] = item
        return item

    def get(self, item_id: str) -> AgendaItemRecord | None:
        return self._items.get(item_id)

    def transition(self, *, item_id: str, to_status: str, actor: str) -> TransitionResult | None:
        item = self.get(item_id)
        if item is None:
            return None
        result = validate_agenda_item_transition(
            agenda_item_id=item_id,
            from_status=item.status,
            to_status=to_status,
            actor=actor,
        )
        item.audit_entries.append(result.audit_entry)
        if result.allowed:
            item.status = to_status
        return result


def validate_agenda_item_transition(
    *,
    agenda_item_id: str,
    from_status: str,
    to_status: str,
    actor: str,
) -> TransitionResult:
    """Validate one agenda item lifecycle transition and produce an audit entry."""
    base_entry = {
        "agenda_item_id": agenda_item_id,
        "actor": actor,
        "from_status": from_status,
        "to_status": to_status,
    }

    if from_status not in AGENDA_ITEM_LIFECYCLE:
        return TransitionResult(
            allowed=False,
            http_status=422,
            message=f"Unknown current status {from_status}. Use one of {', '.join(AGENDA_ITEM_LIFECYCLE)}.",
            audit_entry={
                **base_entry,
                "outcome": "rejected",
                "reason": "unknown current agenda item status",
            },
        )

    if to_status not in AGENDA_ITEM_LIFECYCLE:
        return TransitionResult(
            allowed=False,
            http_status=422,
            message=f"Unknown requested status {to_status}. Use one of {', '.join(AGENDA_ITEM_LIFECYCLE)}.",
            audit_entry={
                **base_entry,
                "outcome": "rejected",
                "reason": "unknown requested agenda item status",
            },
        )

    expected = VALID_TRANSITIONS.get(from_status)
    if expected == to_status:
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

    next_status = expected if expected is not None else "no further status"
    return TransitionResult(
        allowed=False,
        http_status=409,
        message=(
            f"Invalid agenda item lifecycle transition. The canonical next status "
            f"from {from_status} is {next_status}. Next valid status is {next_status}."
        ),
        audit_entry={
            **base_entry,
            "outcome": "rejected",
            "reason": "invalid agenda item lifecycle transition",
        },
    )


__all__ = [
    "AGENDA_ITEM_LIFECYCLE",
    "VALID_TRANSITIONS",
    "AgendaItemRecord",
    "AgendaItemStore",
    "TransitionResult",
    "validate_agenda_item_transition",
]
