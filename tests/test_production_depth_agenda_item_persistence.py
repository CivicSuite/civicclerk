from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.agenda_lifecycle import AgendaItemRepository
from civicclerk.main import app


def test_agenda_item_records_persist_status_and_audit_entries(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'agenda-items.db'}"
    first = AgendaItemRepository(db_url=db_url)
    item = first.create(title="Adopt safe streets plan", department_name="Public Works")

    allowed = first.transition(item_id=item.id, to_status="SUBMITTED", actor="clerk@example.gov")
    rejected = first.transition(item_id=item.id, to_status="POSTED", actor="clerk@example.gov")

    second = AgendaItemRepository(db_url=db_url)
    persisted = second.get(item.id)

    assert allowed is not None
    assert allowed.allowed is True
    assert rejected is not None
    assert rejected.allowed is False
    assert persisted is not None
    assert persisted.status == "SUBMITTED"
    assert [entry["outcome"] for entry in persisted.audit_entries] == ["allowed", "rejected"]
    assert persisted.audit_entries[-1]["to_status"] == "POSTED"


@pytest.mark.asyncio
async def test_api_agenda_items_use_configured_database(monkeypatch, tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'api-agenda-items.db'}"
    monkeypatch.setenv("CIVICCLERK_AGENDA_ITEM_DB_URL", db_url)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/agenda-items",
            json={
                "title": "Approve downtown study",
                "department_name": "Planning",
            },
        )
        transitioned = await client.post(
            f"/agenda-items/{created.json()['id']}/transitions",
            json={
                "to_status": "SUBMITTED",
                "actor": "clerk@example.gov",
            },
        )

    second = AgendaItemRepository(db_url=db_url)
    persisted = second.get(created.json()["id"])

    assert created.status_code == 201
    assert transitioned.status_code == 200
    assert transitioned.json()["status"] == "SUBMITTED"
    assert persisted is not None
    assert persisted.title == "Approve downtown study"
    assert persisted.status == "SUBMITTED"
    assert persisted.audit_entries[-1]["reason"] == "transition allowed"
