"""Packet snapshot and notice compliance helpers for CivicClerk."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4


SPECIAL_NOTICE_TYPES = {"special", "emergency"}


@dataclass(frozen=True)
class PacketSnapshot:
    id: str
    meeting_id: str
    version: int
    agenda_item_ids: tuple[str, ...]
    actor: str

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "version": self.version,
            "agenda_item_ids": list(self.agenda_item_ids),
            "actor": self.actor,
        }


class PacketStore:
    """In-memory packet version store until DB-backed workflow persistence lands."""

    def __init__(self) -> None:
        self._snapshots: dict[str, list[PacketSnapshot]] = {}

    def create_snapshot(
        self,
        *,
        meeting_id: str,
        agenda_item_ids: list[str],
        actor: str,
    ) -> PacketSnapshot:
        existing = self._snapshots.setdefault(meeting_id, [])
        snapshot = PacketSnapshot(
            id=str(uuid4()),
            meeting_id=meeting_id,
            version=len(existing) + 1,
            agenda_item_ids=tuple(agenda_item_ids),
            actor=actor,
        )
        existing.append(snapshot)
        return snapshot

    def list_snapshots(self, meeting_id: str) -> list[PacketSnapshot]:
        return list(self._snapshots.get(meeting_id, []))


@dataclass(frozen=True)
class NoticeComplianceResult:
    meeting_id: str
    notice_type: str
    scheduled_start: datetime
    posted_at: datetime
    minimum_notice_hours: int
    deadline_at: datetime
    statutory_basis: str | None
    approved_by: str | None
    compliant: bool
    http_status: int
    warnings: list[dict[str, str]]

    def public_dict(self) -> dict:
        return {
            "meeting_id": self.meeting_id,
            "notice_type": self.notice_type,
            "scheduled_start": self.scheduled_start.isoformat(),
            "posted_at": self.posted_at.isoformat(),
            "minimum_notice_hours": self.minimum_notice_hours,
            "deadline_at": self.deadline_at.isoformat(),
            "statutory_basis": self.statutory_basis,
            "approved_by": self.approved_by,
            "compliant": self.compliant,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class PostedNotice:
    id: str
    result: NoticeComplianceResult

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            **self.result.public_dict(),
            "posted": True,
        }


class NoticeStore:
    """In-memory posted notice store until DB-backed workflow persistence lands."""

    def __init__(self) -> None:
        self._notices: dict[str, list[PostedNotice]] = {}

    def create(self, result: NoticeComplianceResult) -> PostedNotice:
        notice = PostedNotice(id=str(uuid4()), result=result)
        self._notices.setdefault(result.meeting_id, []).append(notice)
        return notice

    def list_notices(self, meeting_id: str) -> list[PostedNotice]:
        return list(self._notices.get(meeting_id, []))


def evaluate_notice_compliance(
    *,
    meeting_id: str,
    notice_type: str,
    scheduled_start: datetime,
    posted_at: datetime,
    minimum_notice_hours: int,
    statutory_basis: str | None,
    approved_by: str | None,
) -> NoticeComplianceResult:
    normalized_notice_type = notice_type.strip().lower()
    deadline_at = scheduled_start - timedelta(hours=minimum_notice_hours)
    warnings: list[dict[str, str]] = []

    if normalized_notice_type in SPECIAL_NOTICE_TYPES and not statutory_basis:
        warnings.append(
            {
                "code": "missing_statutory_basis",
                "message": "Special and emergency notices require a statutory basis.",
                "fix": "Add the statutory basis authorizing this meeting type before posting public notice.",
            }
        )

    if posted_at > deadline_at:
        warnings.append(
            {
                "code": "notice_deadline_missed",
                "message": "Notice was posted after the required deadline.",
                "fix": "Move the meeting, document the legal exception, or obtain attorney/clerk approval before posting.",
            }
        )

    if not approved_by:
        warnings.append(
            {
                "code": "human_approval_required",
                "message": "Public notice posting requires a named clerk or authorized approver.",
                "fix": "Provide approved_by before posting public notice.",
            }
        )

    status = _status_for_warnings(warnings)
    return NoticeComplianceResult(
        meeting_id=meeting_id,
        notice_type=normalized_notice_type,
        scheduled_start=scheduled_start,
        posted_at=posted_at,
        minimum_notice_hours=minimum_notice_hours,
        deadline_at=deadline_at,
        statutory_basis=statutory_basis,
        approved_by=approved_by,
        compliant=not warnings,
        http_status=status,
        warnings=warnings,
    )


def _status_for_warnings(warnings: list[dict[str, str]]) -> int:
    if not warnings:
        return 200
    if warnings[0]["code"] == "human_approval_required":
        return 403
    return 422


__all__ = [
    "NoticeComplianceResult",
    "NoticeStore",
    "PacketSnapshot",
    "PacketStore",
    "PostedNotice",
    "evaluate_notice_compliance",
]
