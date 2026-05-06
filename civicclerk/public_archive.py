"""Public meeting calendar and archive helpers with permission-aware filtering."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

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
        record = PublicCommentRecord(
            id=str(uuid4()),
            public_record_id=public_record.id,
            commenter_name=commenter_name.strip(),
            comment=comment.strip(),
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


__all__ = [
    "CLOSED_SESSION_VISIBILITY",
    "PERMITTED_CLOSED_SESSION_ROLES",
    "PUBLIC_VISIBILITY",
    "PublicArchiveStore",
    "PublicCommentRecord",
    "PublicCommentStore",
    "PublicMeetingRecord",
    "can_view_closed_sessions",
    "normalize_visibility",
]
