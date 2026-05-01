"""Minutes drafting helpers with citation and provenance validation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from civiccore.ingest import (
    CitedSentence as MinutesSentence,
    SourceMaterial,
    validate_cited_sentences,
)

from civicclerk.prompt_library import (
    expected_prompt_version_hint,
    is_known_prompt_version,
)

@dataclass(frozen=True)
class MinutesProvenance:
    model: str
    prompt_version: str
    data_sources: tuple[str, ...]
    human_approver: str

    def public_dict(self) -> dict[str, str | list[str]]:
        return {
            "model": self.model,
            "prompt_version": self.prompt_version,
            "data_sources": list(self.data_sources),
            "human_approver": self.human_approver,
        }


@dataclass(frozen=True)
class MinutesDraft:
    id: str
    meeting_id: str
    status: str
    sentences: tuple[MinutesSentence, ...]
    source_materials: tuple[SourceMaterial, ...]
    provenance: MinutesProvenance
    adopted: bool = False
    posted: bool = False

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "status": self.status,
            "sentences": [sentence.public_dict() for sentence in self.sentences],
            "source_materials": [source.public_dict() for source in self.source_materials],
            "provenance": self.provenance.public_dict(),
            "adopted": self.adopted,
            "posted": self.posted,
        }


@dataclass(frozen=True)
class MinutesValidationError:
    message: str
    fix: str


class MinutesDraftStore:
    """In-memory minutes draft store until DB-backed persistence lands."""

    def __init__(self) -> None:
        self._drafts: dict[str, MinutesDraft] = {}
        self._drafts_by_meeting: dict[str, list[str]] = {}

    def create_draft(
        self,
        *,
        meeting_id: str,
        model: str,
        prompt_version: str,
        human_approver: str,
        source_materials: list[SourceMaterial],
        sentences: list[MinutesSentence],
    ) -> MinutesDraft | MinutesValidationError:
        if not is_known_prompt_version(prompt_version):
            expected = expected_prompt_version_hint()
            return MinutesValidationError(
                message="Minutes drafts must use a prompt version from the CivicClerk YAML prompt library.",
                fix=f"Use prompt_version '{expected}' or another version returned by the prompt library.",
            )

        validation_error = validate_minutes_draft(
            source_materials=source_materials,
            sentences=sentences,
        )
        if validation_error is not None:
            return validation_error

        source_ids = tuple(source.source_id for source in source_materials)
        draft = MinutesDraft(
            id=str(uuid4()),
            meeting_id=meeting_id,
            status="DRAFT",
            sentences=tuple(sentences),
            source_materials=tuple(source_materials),
            provenance=MinutesProvenance(
                model=model,
                prompt_version=prompt_version,
                data_sources=source_ids,
                human_approver=human_approver,
            ),
        )
        self._drafts[draft.id] = draft
        self._drafts_by_meeting.setdefault(meeting_id, []).append(draft.id)
        return draft

    def get_draft(self, draft_id: str) -> MinutesDraft | None:
        return self._drafts.get(draft_id)

    def list_drafts(self, meeting_id: str) -> list[MinutesDraft]:
        return [
            self._drafts[draft_id]
            for draft_id in self._drafts_by_meeting.get(meeting_id, [])
        ]

    def list_recent(self, *, limit: int = 5) -> list[MinutesDraft]:
        """Return recent citation-gated drafts for the staff dashboard."""

        return list(reversed(list(self._drafts.values())))[:limit]


def validate_minutes_draft(
    *,
    source_materials: list[SourceMaterial],
    sentences: list[MinutesSentence],
) -> MinutesValidationError | None:
    error = validate_cited_sentences(
        source_materials=source_materials,
        sentences=sentences,
    )
    if error is None:
        return None
    if error.message == "Every material sentence must include at least one citation.":
        return MinutesValidationError(
            message="Every material minutes sentence must include at least one citation.",
            fix="Add source citations to each sentence before accepting AI-drafted minutes.",
        )
    if error.message == "Generated sentence cites an unknown source.":
        return MinutesValidationError(
            message="Minutes sentence cites an unknown source.",
            fix=error.fix,
        )
    return MinutesValidationError(message=error.message, fix=error.fix)


__all__ = [
    "MinutesDraft",
    "MinutesDraftStore",
    "MinutesProvenance",
    "MinutesSentence",
    "MinutesValidationError",
    "SourceMaterial",
    "validate_minutes_draft",
]
