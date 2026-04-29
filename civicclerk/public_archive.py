"""Public meeting calendar and archive helpers with permission-aware filtering."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


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
    closed_session_notes: str | None = None

    def public_dict(self, *, include_closed: bool = False) -> dict[str, str | None]:
        payload = {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "title": self.title,
            "posted_agenda": self.posted_agenda,
            "posted_packet": self.posted_packet,
            "approved_minutes": self.approved_minutes,
        }
        if include_closed:
            payload["visibility"] = self.visibility
            payload["closed_session_notes"] = self.closed_session_notes
        return payload


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
        closed_session_notes: str | None = None,
    ) -> PublicMeetingRecord:
        record = PublicMeetingRecord(
            id=str(uuid4()),
            meeting_id=meeting_id,
            title=title,
            visibility=normalize_visibility(visibility),
            posted_agenda=posted_agenda,
            posted_packet=posted_packet,
            approved_minutes=approved_minutes,
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
        normalized_query = query.strip().lower()
        results: list[PublicMeetingRecord] = []
        for record in self._records.values():
            if record.visibility != PUBLIC_VISIBILITY and not include_closed:
                continue
            if _record_matches(record, normalized_query, include_closed=include_closed):
                results.append(record)
        return results


def normalize_visibility(visibility: str) -> str:
    return visibility.strip().lower()


def can_view_closed_sessions(roles: set[str] | frozenset[str] | list[str] | tuple[str, ...]) -> bool:
    normalized_roles = {role.strip().lower() for role in roles if role.strip()}
    return not normalized_roles.isdisjoint(PERMITTED_CLOSED_SESSION_ROLES)


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
    ).lower()
    return query in searchable_text


__all__ = [
    "CLOSED_SESSION_VISIBILITY",
    "PERMITTED_CLOSED_SESSION_ROLES",
    "PUBLIC_VISIBILITY",
    "PublicArchiveStore",
    "PublicMeetingRecord",
    "can_view_closed_sessions",
    "normalize_visibility",
]
