"""Motion, vote, and action-item capture helpers for CivicClerk."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class MotionRecord:
    id: str
    meeting_id: str
    text: str
    actor: str
    agenda_item_id: str | None = None
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
        correction_of_id: str | None = None,
        correction_reason: str | None = None,
    ) -> MotionRecord:
        motion = MotionRecord(
            id=str(uuid4()),
            meeting_id=meeting_id,
            agenda_item_id=agenda_item_id,
            text=text,
            actor=actor,
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


__all__ = [
    "ActionItemRecord",
    "MotionRecord",
    "MotionVoteStore",
    "VoteRecord",
]
