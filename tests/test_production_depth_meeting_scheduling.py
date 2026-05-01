from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app
from civicclerk.meeting_lifecycle import MeetingScheduleUpdateError, MeetingStore


def test_meeting_store_persists_schedule_fields_and_edit_audit(tmp_path: Path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'meeting-scheduling.db'}"
    store = MeetingStore(db_url=db_url)
    meeting = store.create(
        title="Original Council Meeting",
        meeting_type="regular",
        meeting_body_id="body-council",
        scheduled_start=datetime(2026, 5, 5, 18, 0, tzinfo=UTC),
        location="Council Chambers",
    )

    updated = store.update_schedule(
        meeting_id=meeting.id,
        actor="clerk@example.gov",
        title="Updated Council Meeting",
        meeting_type="special",
        meeting_body_id="body-planning",
        scheduled_start=datetime(2026, 5, 6, 19, 30, tzinfo=UTC),
        location="Room 204",
    )

    assert updated is not None
    assert updated.title == "Updated Council Meeting"
    assert updated.meeting_type == "special"
    assert updated.meeting_body_id == "body-planning"
    assert updated.location == "Room 204"
    assert updated.audit_entries[-1]["reason"] == "meeting schedule updated"
    assert updated.audit_entries[-1]["changed_fields"] == (
        "location,meeting_body_id,meeting_type,scheduled_start,title"
    )

    reopened = MeetingStore(db_url=db_url)
    persisted = reopened.get(meeting.id)
    assert persisted is not None
    assert persisted.title == "Updated Council Meeting"
    assert persisted.scheduled_start == datetime(2026, 5, 6, 19, 30, tzinfo=UTC)
    assert persisted.audit_entries[-1]["actor"] == "clerk@example.gov"


def test_meeting_store_blocks_schedule_edits_after_lock_point(tmp_path: Path) -> None:
    store = MeetingStore()
    meeting = store.create(title="Live Meeting", meeting_type="regular")
    meeting.status = "IN_PROGRESS"
    store._meetings[meeting.id] = meeting

    with pytest.raises(MeetingScheduleUpdateError) as error:
        store.update_schedule(
            meeting_id=meeting.id,
            actor="clerk@example.gov",
            title="Renamed After Start",
        )

    assert "locked" in error.value.message
    assert "new replacement meeting" in error.value.fix


@pytest.mark.asyncio
async def test_api_creates_and_updates_scheduled_meeting_with_body_and_location(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import civicclerk.main as main_module

    db_url = f"sqlite+pysqlite:///{tmp_path / 'api-scheduling.db'}"
    body_db_url = f"sqlite+pysqlite:///{tmp_path / 'api-scheduling-bodies.db'}"
    monkeypatch.setenv("CIVICCLERK_MEETING_DB_URL", db_url)
    monkeypatch.setenv("CIVICCLERK_MEETING_BODY_DB_URL", body_db_url)
    main_module._meeting_store = None
    main_module._meeting_db_url = None
    main_module._meeting_body_repository = None
    main_module._meeting_body_db_url = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        council = await client.post(
            "/meeting-bodies",
            json={"name": "City Council", "body_type": "city_council"},
        )
        planning = await client.post(
            "/meeting-bodies",
            json={"name": "Planning Commission", "body_type": "commission"},
        )
        council_id = council.json()["id"]
        planning_id = planning.json()["id"]
        created = await client.post(
            "/meetings",
            json={
                "title": "City Council Regular Meeting",
                "meeting_type": "regular",
                "meeting_body_id": council_id,
                "scheduled_start": "2026-05-05T18:00:00Z",
                "location": "Council Chambers",
            },
        )
        assert created.status_code == 201
        meeting_id = created.json()["id"]
        assert created.json()["meeting_body_id"] == council_id
        assert created.json()["location"] == "Council Chambers"

        updated = await client.patch(
            f"/meetings/{meeting_id}",
            json={
                "title": "City Council Special Meeting",
                "meeting_type": "special",
                "meeting_body_id": planning_id,
                "scheduled_start": "2026-05-06T19:30:00Z",
                "location": "Room 204",
                "actor": "deputy-clerk@example.gov",
            },
        )

        assert updated.status_code == 200
        assert updated.json()["title"] == "City Council Special Meeting"
        assert updated.json()["meeting_body_id"] == planning_id
        assert updated.json()["location"] == "Room 204"

        audit = await client.get(f"/meetings/{meeting_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["entries"][-1]["actor"] == "deputy-clerk@example.gov"
        assert audit.json()["entries"][-1]["reason"] == "meeting schedule updated"

    main_module._meeting_store = None
    main_module._meeting_db_url = None
    main_module._meeting_body_repository = None
    main_module._meeting_body_db_url = None


@pytest.mark.asyncio
async def test_api_rejects_missing_or_inactive_meeting_body(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import civicclerk.main as main_module

    monkeypatch.setenv("CIVICCLERK_MEETING_DB_URL", f"sqlite+pysqlite:///{tmp_path / 'body-guard-meetings.db'}")
    monkeypatch.setenv("CIVICCLERK_MEETING_BODY_DB_URL", f"sqlite+pysqlite:///{tmp_path / 'body-guard-bodies.db'}")
    main_module._meeting_store = None
    main_module._meeting_db_url = None
    main_module._meeting_body_repository = None
    main_module._meeting_body_db_url = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        missing = await client.post(
            "/meetings",
            json={
                "title": "Missing Body Meeting",
                "meeting_type": "regular",
                "meeting_body_id": "not-a-real-body",
            },
        )
        assert missing.status_code == 422
        assert missing.json()["detail"]["message"] == "Meeting body does not exist."
        assert "GET /meeting-bodies?active_only=true" in missing.json()["detail"]["fix"]

        body = await client.post(
            "/meeting-bodies",
            json={"name": "Inactive Board", "body_type": "board", "is_active": False},
        )
        inactive = await client.post(
            "/meetings",
            json={
                "title": "Inactive Body Meeting",
                "meeting_type": "regular",
                "meeting_body_id": body.json()["id"],
            },
        )
        assert inactive.status_code == 409
        assert inactive.json()["detail"]["message"] == "Meeting body is inactive."
        assert "Reactivate the body" in inactive.json()["detail"]["fix"]

    main_module._meeting_store = None
    main_module._meeting_db_url = None
    main_module._meeting_body_repository = None
    main_module._meeting_body_db_url = None


@pytest.mark.asyncio
async def test_api_meeting_schedule_update_has_actionable_validation() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={"title": "No-op Update Meeting", "meeting_type": "regular"},
        )

        rejected = await client.patch(f"/meetings/{created.json()['id']}", json={})

        assert rejected.status_code == 422
        assert rejected.json()["detail"]["message"] == (
            "Meeting update did not include any schedule fields."
        )
        assert "Send at least one" in rejected.json()["detail"]["fix"]
