from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app
from civicclerk.meeting_body import MeetingBodyRepository


def test_meeting_body_repository_persists_crud_without_hard_delete(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'meeting-bodies.db'}"
    first = MeetingBodyRepository(db_url=db_url)

    created = first.create(name="City Council", body_type="council")
    updated = first.update(
        body_id=str(created.id),
        name="Brookfield City Council",
        body_type="city_council",
    )
    deactivated = first.deactivate(str(created.id))

    second = MeetingBodyRepository(db_url=db_url)
    persisted = second.get(str(created.id))

    assert updated is not None
    assert updated.name == "Brookfield City Council"
    assert deactivated is not None
    assert deactivated.is_active is False
    assert persisted is not None
    assert persisted.is_active is False
    assert second.list(active_only=True) == []


@pytest.mark.asyncio
async def test_api_meeting_body_crud_uses_configured_database(monkeypatch, tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'api-meeting-bodies.db'}"
    monkeypatch.setenv("CIVICCLERK_MEETING_BODY_DB_URL", db_url)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meeting-bodies",
            json={"name": "Planning Commission", "body_type": "commission"},
        )
        body_id = created.json()["id"]
        listed = await client.get("/meeting-bodies")
        updated = await client.patch(
            f"/meeting-bodies/{body_id}",
            json={"name": "Planning and Zoning Commission", "is_active": True},
        )
        deactivated = await client.delete(f"/meeting-bodies/{body_id}")
        active_only = await client.get("/meeting-bodies?active_only=true")
        missing = await client.get("/meeting-bodies/not-a-uuid")

    second = MeetingBodyRepository(db_url=db_url)
    persisted = second.get(body_id)

    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert updated.status_code == 200
    assert updated.json()["name"] == "Planning and Zoning Commission"
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert active_only.status_code == 200
    assert active_only.json()["meeting_bodies"] == []
    assert missing.status_code == 404
    assert persisted is not None
    assert persisted.is_active is False
