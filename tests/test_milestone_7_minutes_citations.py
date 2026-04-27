from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_minutes_draft_requires_sentence_level_citations_and_records_provenance() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Minutes Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = meeting.json()["id"]

        draft = await client.post(
            f"/meetings/{meeting_id}/minutes/drafts",
            json={
                "model": "ollama/gemma4",
                "prompt_version": "minutes_draft@0.1.0",
                "human_approver": "clerk@example.gov",
                "source_materials": [
                    {
                        "source_id": "motion-1",
                        "label": "Motion text",
                        "text": "Council approved the sidewalk repair packet.",
                    },
                    {
                        "source_id": "vote-1",
                        "label": "Vote record",
                        "text": "The motion passed 5-0.",
                    },
                ],
                "sentences": [
                    {
                        "text": "Council approved the sidewalk repair packet.",
                        "citations": ["motion-1"],
                    },
                    {
                        "text": "The motion passed 5-0.",
                        "citations": ["vote-1"],
                    },
                ],
            },
        )

    assert draft.status_code == 201
    payload = draft.json()
    assert payload["meeting_id"] == meeting_id
    assert payload["status"] == "DRAFT"
    assert payload["adopted"] is False
    assert payload["posted"] is False
    assert payload["provenance"] == {
        "model": "ollama/gemma4",
        "prompt_version": "minutes_draft@0.1.0",
        "data_sources": ["motion-1", "vote-1"],
        "human_approver": "clerk@example.gov",
    }
    assert payload["sentences"][0]["citations"] == ["motion-1"]
    assert payload["sentences"][1]["citations"] == ["vote-1"]


@pytest.mark.asyncio
async def test_minutes_draft_rejects_uncited_material_output_with_actionable_error() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Uncited Minutes Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        rejected = await client.post(
            f"/meetings/{meeting.json()['id']}/minutes/drafts",
            json={
                "model": "ollama/gemma4",
                "prompt_version": "minutes_draft@0.1.0",
                "human_approver": "clerk@example.gov",
                "source_materials": [
                    {
                        "source_id": "motion-1",
                        "label": "Motion text",
                        "text": "Council approved the sidewalk repair packet.",
                    }
                ],
                "sentences": [
                    {
                        "text": "Council approved the sidewalk repair packet.",
                        "citations": [],
                    }
                ],
            },
        )

    assert rejected.status_code == 422
    detail = rejected.json()["detail"]
    assert detail["message"] == "Every material minutes sentence must include at least one citation."
    assert "Add source citations to each sentence" in detail["fix"]


@pytest.mark.asyncio
async def test_minutes_draft_rejects_unknown_citation_source_with_actionable_error() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Bad Citation Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        rejected = await client.post(
            f"/meetings/{meeting.json()['id']}/minutes/drafts",
            json={
                "model": "ollama/gemma4",
                "prompt_version": "minutes_draft@0.1.0",
                "human_approver": "clerk@example.gov",
                "source_materials": [
                    {
                        "source_id": "motion-1",
                        "label": "Motion text",
                        "text": "Council approved the sidewalk repair packet.",
                    }
                ],
                "sentences": [
                    {
                        "text": "Council approved the sidewalk repair packet.",
                        "citations": ["not-a-source"],
                    }
                ],
            },
        )

    assert rejected.status_code == 422
    detail = rejected.json()["detail"]
    assert detail["message"] == "Minutes sentence cites an unknown source."
    assert "Use one of the source_materials source_id values" in detail["fix"]


@pytest.mark.asyncio
async def test_minutes_draft_requires_human_approver_before_ai_output_is_accepted() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Approver Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        rejected = await client.post(
            f"/meetings/{meeting.json()['id']}/minutes/drafts",
            json={
                "model": "ollama/gemma4",
                "prompt_version": "minutes_draft@0.1.0",
                "source_materials": [
                    {
                        "source_id": "motion-1",
                        "label": "Motion text",
                        "text": "Council approved the sidewalk repair packet.",
                    }
                ],
                "sentences": [
                    {
                        "text": "Council approved the sidewalk repair packet.",
                        "citations": ["motion-1"],
                    }
                ],
            },
        )

    assert rejected.status_code == 422
    assert "human_approver" in rejected.text


@pytest.mark.asyncio
async def test_minutes_adoption_and_public_posting_are_not_automatic() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "No Auto Adopt Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        draft = await client.post(
            f"/meetings/{meeting.json()['id']}/minutes/drafts",
            json={
                "model": "ollama/gemma4",
                "prompt_version": "minutes_draft@0.1.0",
                "human_approver": "clerk@example.gov",
                "source_materials": [
                    {
                        "source_id": "motion-1",
                        "label": "Motion text",
                        "text": "Council approved the sidewalk repair packet.",
                    }
                ],
                "sentences": [
                    {
                        "text": "Council approved the sidewalk repair packet.",
                        "citations": ["motion-1"],
                    }
                ],
            },
        )
        minute_id = draft.json()["id"]
        post_attempt = await client.post(f"/minutes/{minute_id}/post")
        listing = await client.get(f"/meetings/{meeting.json()['id']}/minutes/drafts")

    assert draft.json()["adopted"] is False
    assert draft.json()["posted"] is False
    assert post_attempt.status_code == 409
    detail = post_attempt.json()["detail"]
    assert detail["message"] == "AI-drafted minutes cannot be posted automatically."
    assert "adopt minutes through a human approval workflow" in detail["fix"]
    assert listing.json()["drafts"] == [draft.json()]


def test_docs_record_minutes_citation_scope_without_claiming_archive_or_ui_behavior() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        "CHANGELOG.md": (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "minutes" in lowered, path
        assert "citation" in lowered, path
        assert "provenance" in lowered, path
        assert "archive workflow shipped" not in lowered, path
        assert "ui workflow shipped" not in lowered, path
