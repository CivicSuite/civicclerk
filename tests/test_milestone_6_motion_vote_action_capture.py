from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_api_captured_motion_is_immutable_and_corrections_reference_original() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Motion Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = meeting.json()["id"]

        captured = await client.post(
            f"/meetings/{meeting_id}/motions",
            json={
                "text": "Move to approve the packet as presented.",
                "actor": "clerk@example.gov",
            },
        )
        motion_id = captured.json()["id"]

        put_attempt = await client.put(
            f"/motions/{motion_id}",
            json={"text": "Silently rewrite the legal record."},
        )
        patch_attempt = await client.patch(
            f"/motions/{motion_id}",
            json={"text": "Silently rewrite the legal record."},
        )
        correction = await client.post(
            f"/motions/{motion_id}/corrections",
            json={
                "text": "Move to approve the packet as amended.",
                "actor": "clerk@example.gov",
                "reason": "Clerk correction after audio review.",
            },
        )
        listing = await client.get(f"/meetings/{meeting_id}/motions")

    assert captured.status_code == 201
    assert captured.json()["captured"] is True
    assert captured.json()["correction_of_id"] is None
    for response in (put_attempt, patch_attempt):
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["message"] == "Captured motions are immutable."
        assert "Use POST /motions/{motion_id}/corrections" in detail["fix"]
    assert correction.status_code == 201
    assert correction.json()["correction_of_id"] == motion_id
    assert correction.json()["text"] == "Move to approve the packet as amended."
    assert [motion["id"] for motion in listing.json()["motions"]] == [
        motion_id,
        correction.json()["id"],
    ]


@pytest.mark.asyncio
async def test_api_captured_vote_is_immutable_and_corrections_reference_original() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Vote Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = meeting.json()["id"]
        motion = await client.post(
            f"/meetings/{meeting_id}/motions",
            json={
                "text": "Move to award the contract.",
                "actor": "clerk@example.gov",
            },
        )
        motion_id = motion.json()["id"]

        captured = await client.post(
            f"/motions/{motion_id}/votes",
            json={
                "voter_name": "Council Member Rivera",
                "vote": "aye",
                "actor": "clerk@example.gov",
            },
        )
        vote_id = captured.json()["id"]

        put_attempt = await client.put(
            f"/votes/{vote_id}",
            json={"vote": "nay"},
        )
        patch_attempt = await client.patch(
            f"/votes/{vote_id}",
            json={"vote": "abstain"},
        )
        correction = await client.post(
            f"/votes/{vote_id}/corrections",
            json={
                "vote": "abstain",
                "actor": "clerk@example.gov",
                "reason": "Member clarified abstention before minutes drafting.",
            },
        )
        listing = await client.get(f"/motions/{motion_id}/votes")

    assert captured.status_code == 201
    assert captured.json()["vote"] == "aye"
    assert captured.json()["captured"] is True
    assert captured.json()["correction_of_id"] is None
    for response in (put_attempt, patch_attempt):
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["message"] == "Captured votes are immutable."
        assert "Use POST /votes/{vote_id}/corrections" in detail["fix"]
    assert correction.status_code == 201
    assert correction.json()["correction_of_id"] == vote_id
    assert correction.json()["vote"] == "abstain"
    assert [vote["id"] for vote in listing.json()["votes"]] == [
        vote_id,
        correction.json()["id"],
    ]


@pytest.mark.asyncio
async def test_action_items_link_to_meeting_outcomes() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Action Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = meeting.json()["id"]
        motion = await client.post(
            f"/meetings/{meeting_id}/motions",
            json={
                "text": "Direct Public Works to inspect sidewalk repairs.",
                "actor": "clerk@example.gov",
            },
        )
        motion_id = motion.json()["id"]

        created = await client.post(
            f"/meetings/{meeting_id}/action-items",
            json={
                "description": "Public Works to inspect sidewalk repairs and report back.",
                "source_motion_id": motion_id,
                "assigned_to": "Public Works",
                "actor": "clerk@example.gov",
            },
        )
        listing = await client.get(f"/meetings/{meeting_id}/action-items")

    assert created.status_code == 201
    assert created.json()["meeting_id"] == meeting_id
    assert created.json()["source_motion_id"] == motion_id
    assert created.json()["status"] == "OPEN"
    assert listing.json()["action_items"] == [created.json()]


@pytest.mark.asyncio
async def test_action_item_rejects_motion_from_different_meeting_with_actionable_error() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        first = await client.post(
            "/meetings",
            json={
                "title": "Source Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        second = await client.post(
            "/meetings",
            json={
                "title": "Target Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-06T19:00:00Z",
            },
        )
        motion = await client.post(
            f"/meetings/{first.json()['id']}/motions",
            json={
                "text": "Direct Finance to return with a fee study.",
                "actor": "clerk@example.gov",
            },
        )

        rejected = await client.post(
            f"/meetings/{second.json()['id']}/action-items",
            json={
                "description": "Finance to return with a fee study.",
                "source_motion_id": motion.json()["id"],
                "actor": "clerk@example.gov",
            },
        )

    assert rejected.status_code == 422
    detail = rejected.json()["detail"]
    assert detail["message"] == "Action item source motion belongs to a different meeting."
    assert "Use a motion captured for this meeting" in detail["fix"]


def test_docs_record_motion_vote_action_scope_without_claiming_minutes_or_archive_behavior() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        "CHANGELOG.md": (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "motion" in lowered, path
        assert "vote" in lowered, path
        assert "action item" in lowered or "action-item" in lowered, path
        assert "minutes drafting shipped" not in lowered, path
        assert "archive workflow shipped" not in lowered, path
