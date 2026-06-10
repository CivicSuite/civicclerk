from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from civicclerk.minutes import (
    MinutesDraftRepository,
    MinutesSentence,
    MinutesValidationError,
    SourceMaterial,
)

ROOT = Path(__file__).resolve().parents[1]


def _source() -> SourceMaterial:
    return SourceMaterial(
        source_id="motion-sidewalk-contract",
        label="Captured motion and roll-call vote",
        text="Council approved the sidewalk repair contract by a 3-1 vote.",
    )


def test_minutes_drafts_persist_across_repository_instances(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'minutes.db'}"
    meeting_id = str(uuid4())

    first = MinutesDraftRepository(db_url=db_url)
    draft = first.create_draft(
        meeting_id=meeting_id,
        model="ollama/gemma4",
        prompt_version="minutes_draft@0.1.0",
        human_approver="clerk@example.gov",
        source_materials=[_source()],
        sentences=[
            MinutesSentence(
                text="Council approved the sidewalk repair contract by a 3-1 vote.",
                citations=("motion-sidewalk-contract",),
            )
        ],
    )
    assert hasattr(draft, "public_dict"), getattr(draft, "message", draft)

    second = MinutesDraftRepository(db_url=db_url)
    drafts = second.list_drafts(meeting_id)

    assert [d.id for d in drafts] == [draft.id]
    assert drafts[0].public_dict() == {
        "id": draft.id,
        "meeting_id": meeting_id,
        "status": "DRAFT",
        "sentences": [
            {
                "text": "Council approved the sidewalk repair contract by a 3-1 vote.",
                "citations": ["motion-sidewalk-contract"],
            }
        ],
        "source_materials": [
            {
                "source_id": "motion-sidewalk-contract",
                "label": "Captured motion and roll-call vote",
                "text": "Council approved the sidewalk repair contract by a 3-1 vote.",
            }
        ],
        "provenance": {
            "model": "ollama/gemma4",
            "prompt_version": "minutes_draft@0.1.0",
            "data_sources": ["motion-sidewalk-contract"],
            "human_approver": "clerk@example.gov",
        },
        "adopted": False,
        "posted": False,
    }
    assert second.get_draft(draft.id) is not None
    assert second.get_draft("not-a-uuid") is None
    assert [d.id for d in second.list_recent(limit=1)] == [draft.id]


def test_repository_enforces_prompt_library_and_citation_gates(tmp_path) -> None:
    repo = MinutesDraftRepository(db_url=f"sqlite:///{tmp_path / 'gates.db'}")
    bad_prompt = repo.create_draft(
        meeting_id=str(uuid4()),
        model="ollama/gemma4",
        prompt_version="not-a-known-version",
        human_approver="clerk@example.gov",
        source_materials=[_source()],
        sentences=[
            MinutesSentence(text="Cited sentence.", citations=("motion-sidewalk-contract",))
        ],
    )
    uncited = repo.create_draft(
        meeting_id=str(uuid4()),
        model="ollama/gemma4",
        prompt_version="minutes_draft@0.1.0",
        human_approver="clerk@example.gov",
        source_materials=[_source()],
        sentences=[MinutesSentence(text="No citation here.", citations=())],
    )

    assert isinstance(bad_prompt, MinutesValidationError)
    assert "prompt library" in bad_prompt.message.lower() or "prompt version" in bad_prompt.fix.lower()
    assert isinstance(uncited, MinutesValidationError)
    assert "citation" in uncited.message.lower()


def test_concurrent_draft_creation_keeps_audit_chain_intact(tmp_path) -> None:
    repo = MinutesDraftRepository(db_url=f"sqlite:///{tmp_path / 'concurrent.db'}")
    meeting_id = str(uuid4())

    def create_batch(worker_index: int) -> None:
        for sequence in range(25):
            draft = repo.create_draft(
                meeting_id=meeting_id,
                model="ollama/gemma4",
                prompt_version="minutes_draft@0.1.0",
                human_approver="clerk@example.gov",
                source_materials=[_source()],
                sentences=[
                    MinutesSentence(
                        text="Council approved the sidewalk repair contract by a 3-1 vote.",
                        citations=("motion-sidewalk-contract",),
                    )
                ],
            )
            assert hasattr(draft, "public_dict"), getattr(draft, "message", draft)

    # Force frequent thread switches so unsynchronized read-last-hash-then-append
    # interleavings surface deterministically instead of once a month in production.
    original_interval = sys.getswitchinterval()
    try:
        sys.setswitchinterval(1e-6)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(create_batch, range(8)))
    finally:
        sys.setswitchinterval(original_interval)

    assert len(repo.list_drafts(meeting_id)) == 200
    assert len(repo.audit_chain.events) == 200
    assert repo.audit_chain.verify()


def test_migration_0013_adds_model_and_posted_at_and_extends_chain() -> None:
    path = (
        ROOT
        / "civicclerk"
        / "migrations"
        / "versions"
        / "civicclerk_0013_minutes_model_posted.py"
    )
    assert path.exists(), "Missing migration: civicclerk_0013_minutes_model_posted.py"
    text = path.read_text(encoding="utf-8")
    assert 'revision = "civicclerk_0013_minutes_model"' in text
    assert 'down_revision = "civicclerk_0012_action_actor"' in text
    assert '"model"' in text and '"posted_at"' in text and '"minutes"' in text
