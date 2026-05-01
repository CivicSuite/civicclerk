from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from civicclerk.agenda_intake import AgendaIntakeRepository, AgendaReadinessStatus
from civicclerk.main import app


def test_agenda_intake_queue_persists_across_repository_instances(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'agenda-intake.db'}"
    first = AgendaIntakeRepository(db_url=db_url)
    submitted = first.submit(
        title="Approve paving contract",
        department_name="Public Works",
        submitted_by="pw@example.gov",
        summary="Contract award for arterial paving.",
        source_references=[
            {
                "source_id": "staff-report-1",
                "title": "Paving staff report",
                "kind": "document",
                "source_system": "local_file",
                "checksum": "abc123",
            }
        ],
    )

    second = AgendaIntakeRepository(db_url=db_url)
    queue = second.list_queue()

    assert [item.id for item in queue] == [submitted.id]
    assert queue[0].status == "SUBMITTED"
    assert queue[0].readiness_status == AgendaReadinessStatus.PENDING.value
    assert queue[0].source_references[0]["checksum"] == "abc123"
    assert len(queue[0].last_audit_hash) == 64


def test_staff_review_records_ready_or_revision_state_and_audit(tmp_path) -> None:
    repo = AgendaIntakeRepository(db_url=f"sqlite:///{tmp_path / 'agenda-intake.db'}")
    item = repo.submit(
        title="Adopt fee schedule",
        department_name="Finance",
        submitted_by="finance@example.gov",
        summary="Annual fee schedule update.",
        source_references=[{"source_id": "fee-table", "title": "Fee table", "kind": "document"}],
    )

    needs_revision = repo.review(
        item_id=item.id,
        reviewer="clerk@example.gov",
        ready=False,
        notes="Missing city attorney review.",
    )
    ready = repo.review(
        item_id=item.id,
        reviewer="clerk@example.gov",
        ready=True,
        notes="Attorney review attached.",
    )

    assert needs_revision is not None
    assert needs_revision.readiness_status == AgendaReadinessStatus.NEEDS_REVISION.value
    assert ready is not None
    assert ready.readiness_status == AgendaReadinessStatus.READY.value
    assert ready.status == "READY_FOR_CLERK"
    assert len(needs_revision.last_audit_hash) == 64
    assert len(ready.last_audit_hash) == 64
    assert ready.last_audit_hash != needs_revision.last_audit_hash
    assert repo.audit_chain.verify()
    assert [event.action for event in repo.audit_chain.events] == [
        "agenda_intake.submitted",
        "agenda_intake.reviewed",
        "agenda_intake.reviewed",
    ]


def test_staff_review_rejects_unknown_intake_item(tmp_path) -> None:
    repo = AgendaIntakeRepository(db_url=f"sqlite:///{tmp_path / 'agenda-intake.db'}")

    assert repo.review(
        item_id="missing",
        reviewer="clerk@example.gov",
        ready=True,
        notes="Looks fine.",
    ) is None


async def test_api_agenda_intake_submit_list_and_review(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_AGENDA_INTAKE_DB_URL", f"sqlite:///{tmp_path / 'api-intake.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        submitted = await client.post(
            "/agenda-intake",
            json={
                "title": "Approve zoning study",
                "department_name": "Planning",
                "submitted_by": "planning@example.gov",
                "summary": "Study authorization for downtown zoning.",
                "source_references": [
                    {
                        "source_id": "zoning-memo",
                        "title": "Planning memo",
                        "kind": "document",
                    }
                ],
            },
        )
        listed = await client.get("/agenda-intake")
        reviewed = await client.post(
            f"/agenda-intake/{submitted.json()['id']}/review",
            json={
                "reviewer": "clerk@example.gov",
                "ready": True,
                "notes": "Complete for packet assembly.",
            },
        )

    assert submitted.status_code == 201
    assert submitted.json()["readiness_status"] == "PENDING"
    assert len(submitted.json()["last_audit_hash"]) == 64
    assert listed.status_code == 200
    assert listed.json()["items"][0]["title"] == "Approve zoning study"
    assert reviewed.status_code == 200
    assert reviewed.json()["readiness_status"] == "READY"
    assert reviewed.json()["last_audit_hash"] != submitted.json()["last_audit_hash"]


async def test_api_agenda_intake_review_unknown_item_is_actionable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_AGENDA_INTAKE_DB_URL", f"sqlite:///{tmp_path / 'api-intake.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/agenda-intake/missing/review",
            json={
                "reviewer": "clerk@example.gov",
                "ready": True,
                "notes": "Complete.",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"]["fix"] == "Submit the agenda item into the intake queue before review."


async def test_api_agenda_intake_promotes_ready_item_to_agenda_lifecycle(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("CIVICCLERK_AGENDA_INTAKE_DB_URL", f"sqlite:///{tmp_path / 'api-promote-intake.db'}")
    monkeypatch.setenv("CIVICCLERK_AGENDA_ITEM_DB_URL", f"sqlite:///{tmp_path / 'api-promote-agenda.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        submitted = await client.post(
            "/agenda-intake",
            json={
                "title": "Adopt fee schedule",
                "department_name": "Finance",
                "submitted_by": "finance@example.gov",
                "summary": "Annual fee schedule update.",
                "source_references": [
                    {
                        "source_id": "fee-table",
                        "title": "Fee table",
                        "kind": "spreadsheet",
                    }
                ],
            },
        )
        reviewed = await client.post(
            f"/agenda-intake/{submitted.json()['id']}/review",
            json={
                "reviewer": "clerk@example.gov",
                "ready": True,
                "notes": "Attorney review attached.",
            },
        )
        promoted = await client.post(
            f"/agenda-intake/{submitted.json()['id']}/promote",
            json={
                "reviewer": "clerk@example.gov",
                "notes": "Ready for agenda lifecycle.",
            },
        )
        repeated = await client.post(
            f"/agenda-intake/{submitted.json()['id']}/promote",
            json={
                "reviewer": "clerk@example.gov",
                "notes": "Repeated promotion click.",
            },
        )

    assert reviewed.status_code == 200
    assert promoted.status_code == 201
    payload = promoted.json()
    assert payload["message"] == "Agenda intake item promoted into the agenda lifecycle."
    assert payload["agenda_item"]["title"] == "Adopt fee schedule"
    assert payload["agenda_item"]["status"] == "CLERK_ACCEPTED"
    assert payload["intake_item"]["status"] == "PROMOTED_TO_AGENDA"
    assert payload["intake_item"]["promoted_agenda_item_id"] == payload["agenda_item"]["id"]
    assert len(payload["intake_item"]["promotion_audit_hash"]) == 64
    assert payload["next_step"] == "Add the agenda item to the target meeting packet assembly."
    assert repeated.status_code == 200
    assert repeated.json()["message"] == "Agenda intake item was already promoted."
    assert repeated.json()["intake_item"]["promoted_agenda_item_id"] == payload["agenda_item"]["id"]


async def test_api_agenda_intake_promote_requires_ready_review(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_AGENDA_INTAKE_DB_URL", f"sqlite:///{tmp_path / 'api-promote-blocked-intake.db'}")
    monkeypatch.setenv("CIVICCLERK_AGENDA_ITEM_DB_URL", f"sqlite:///{tmp_path / 'api-promote-blocked-agenda.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        submitted = await client.post(
            "/agenda-intake",
            json={
                "title": "Approve paving contract",
                "department_name": "Public Works",
                "submitted_by": "pw@example.gov",
                "summary": "Contract award for arterial paving.",
                "source_references": [
                    {
                        "source_id": "paving-report",
                        "title": "Paving staff report",
                        "kind": "document",
                    }
                ],
            },
        )
        promoted = await client.post(
            f"/agenda-intake/{submitted.json()['id']}/promote",
            json={
                "reviewer": "clerk@example.gov",
                "notes": "Trying before readiness review.",
            },
        )

    assert promoted.status_code == 409
    assert promoted.json()["detail"]["current_readiness_status"] == "PENDING"
    assert promoted.json()["detail"]["fix"] == (
        "Mark the item ready in the clerk review queue, then promote it to agenda work."
    )
