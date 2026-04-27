from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_packet_snapshots_are_versioned_and_immutable() -> None:
    from civicclerk.packet_notice import PacketStore

    store = PacketStore()
    first = store.create_snapshot(
        meeting_id="meeting-123",
        agenda_item_ids=["item-1", "item-2"],
        actor="clerk@example.gov",
    )
    second = store.create_snapshot(
        meeting_id="meeting-123",
        agenda_item_ids=["item-1", "item-2", "item-3"],
        actor="clerk@example.gov",
    )

    assert first.version == 1
    assert second.version == 2
    assert first.agenda_item_ids == ("item-1", "item-2")
    assert second.agenda_item_ids == ("item-1", "item-2", "item-3")
    assert store.list_snapshots("meeting-123")[0].public_dict()["version"] == 1


def test_notice_deadline_check_returns_actionable_warning_when_late() -> None:
    from civicclerk.packet_notice import evaluate_notice_compliance

    scheduled_start = datetime(2026, 5, 5, 19, 0, tzinfo=UTC)
    posted_at = scheduled_start - timedelta(hours=12)

    result = evaluate_notice_compliance(
        meeting_id="meeting-123",
        notice_type="regular",
        scheduled_start=scheduled_start,
        posted_at=posted_at,
        minimum_notice_hours=72,
        statutory_basis="Local open meeting law requires 72 hours posted notice.",
        approved_by="clerk@example.gov",
    )

    assert result.compliant is False
    assert result.http_status == 422
    assert result.deadline_at == scheduled_start - timedelta(hours=72)
    assert result.warnings == [
        {
            "code": "notice_deadline_missed",
            "message": "Notice was posted after the required deadline.",
            "fix": "Move the meeting, document the legal exception, or obtain attorney/clerk approval before posting.",
        }
    ]


@pytest.mark.parametrize("notice_type", ["special", "emergency"])
def test_special_and_emergency_notices_require_statutory_basis(notice_type: str) -> None:
    from civicclerk.packet_notice import evaluate_notice_compliance

    scheduled_start = datetime(2026, 5, 5, 19, 0, tzinfo=UTC)
    posted_at = scheduled_start - timedelta(hours=24)

    result = evaluate_notice_compliance(
        meeting_id="meeting-123",
        notice_type=notice_type,
        scheduled_start=scheduled_start,
        posted_at=posted_at,
        minimum_notice_hours=24,
        statutory_basis=None,
        approved_by="clerk@example.gov",
    )

    assert result.compliant is False
    assert result.http_status == 422
    assert result.warnings[0]["code"] == "missing_statutory_basis"
    assert "Add the statutory basis" in result.warnings[0]["fix"]


def test_public_notice_posting_requires_human_approval() -> None:
    from civicclerk.packet_notice import evaluate_notice_compliance

    scheduled_start = datetime(2026, 5, 5, 19, 0, tzinfo=UTC)
    posted_at = scheduled_start - timedelta(hours=96)

    result = evaluate_notice_compliance(
        meeting_id="meeting-123",
        notice_type="regular",
        scheduled_start=scheduled_start,
        posted_at=posted_at,
        minimum_notice_hours=72,
        statutory_basis="Local open meeting law requires 72 hours posted notice.",
        approved_by=None,
    )

    assert result.compliant is False
    assert result.http_status == 403
    assert result.warnings == [
        {
            "code": "human_approval_required",
            "message": "Public notice posting requires a named clerk or authorized approver.",
            "fix": "Provide approved_by before posting public notice.",
        }
    ]


@pytest.mark.asyncio
async def test_api_packet_snapshots_increment_versions_for_meeting() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Packet Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = created.json()["id"]

        first = await client.post(
            f"/meetings/{meeting_id}/packet-snapshots",
            json={
                "agenda_item_ids": ["item-1", "item-2"],
                "actor": "clerk@example.gov",
            },
        )
        second = await client.post(
            f"/meetings/{meeting_id}/packet-snapshots",
            json={
                "agenda_item_ids": ["item-1", "item-2", "item-3"],
                "actor": "clerk@example.gov",
            },
        )
        listing = await client.get(f"/meetings/{meeting_id}/packet-snapshots")

    assert first.status_code == 201
    assert first.json()["version"] == 1
    assert second.status_code == 201
    assert second.json()["version"] == 2
    assert [snapshot["version"] for snapshot in listing.json()["snapshots"]] == [1, 2]


@pytest.mark.asyncio
async def test_api_notice_check_is_actionable_and_does_not_post_without_approval() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Notice Meeting",
                "meeting_type": "special",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = created.json()["id"]

        check = await client.post(
            f"/meetings/{meeting_id}/notices/check",
            json={
                "notice_type": "special",
                "posted_at": "2026-05-04T19:00:00Z",
                "minimum_notice_hours": 24,
            },
        )
        unapproved_post = await client.post(
            f"/meetings/{meeting_id}/notices/post",
            json={
                "notice_type": "regular",
                "posted_at": "2026-05-01T19:00:00Z",
                "minimum_notice_hours": 72,
                "statutory_basis": "Local open meeting law requires 72 hours posted notice.",
            },
        )

    assert check.status_code == 422
    assert check.json()["detail"]["warnings"][0]["code"] == "missing_statutory_basis"
    assert "Add the statutory basis" in check.json()["detail"]["warnings"][0]["fix"]
    assert unapproved_post.status_code == 403
    assert unapproved_post.json()["detail"]["warnings"][0]["code"] == "human_approval_required"


@pytest.mark.asyncio
async def test_api_notice_check_rejects_naive_scheduled_start_without_500() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Naive Time Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00",
            },
        )

    assert created.status_code == 422
    detail = created.json()["detail"]
    assert detail["message"] == "scheduled_start must include a timezone offset."
    assert "Use an ISO 8601 timestamp with Z or an explicit offset" in detail["fix"]


@pytest.mark.asyncio
async def test_api_notice_posting_records_approved_public_notice() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Approved Notice Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = created.json()["id"]

        posted = await client.post(
            f"/meetings/{meeting_id}/notices/post",
            json={
                "notice_type": "regular",
                "posted_at": "2026-05-01T19:00:00Z",
                "minimum_notice_hours": 72,
                "statutory_basis": "Local open meeting law requires 72 hours posted notice.",
                "approved_by": "clerk@example.gov",
            },
        )

    assert posted.status_code == 201
    assert posted.json()["posted"] is True
    assert posted.json()["approved_by"] == "clerk@example.gov"
    assert posted.json()["warnings"] == []


def test_docs_record_packet_notice_scope_without_claiming_votes_or_minutes_behavior() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        "CHANGELOG.md": (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "packet" in lowered, path
        assert "notice compliance" in lowered, path
        assert "vote capture shipped" not in lowered, path
        assert "minutes drafting shipped" not in lowered, path
