from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient

from civicclerk.main import app
from civicclerk.notice_checklist import NoticeChecklistRepository, NoticeChecklistStatus


def test_notice_checklist_records_persist_warnings_and_audit(tmp_path) -> None:
    repo = NoticeChecklistRepository(db_url=f"sqlite:///{tmp_path / 'notice-checklist.db'}")
    scheduled_start = datetime(2026, 5, 5, 19, 0, tzinfo=UTC)
    posted_at = scheduled_start - timedelta(hours=12)
    record = repo.record_check(
        meeting_id="meeting-123",
        notice_type="regular",
        compliant=False,
        http_status=422,
        warnings=[{"code": "notice_deadline_missed", "fix": "Move the meeting."}],
        deadline_at=scheduled_start - timedelta(hours=72),
        posted_at=posted_at,
        minimum_notice_hours=72,
        statutory_basis="72-hour notice rule",
        approved_by="clerk@example.gov",
        actor="clerk@example.gov",
    )

    second = NoticeChecklistRepository(db_url=f"sqlite:///{tmp_path / 'notice-checklist.db'}")
    records = second.list_for_meeting("meeting-123")

    assert [item.id for item in records] == [record.id]
    assert records[0].status == NoticeChecklistStatus.CHECKED.value
    assert records[0].warnings[0]["code"] == "notice_deadline_missed"
    assert len(records[0].last_audit_hash) == 64


def test_notice_posting_proof_updates_status_and_audit_hash(tmp_path) -> None:
    repo = NoticeChecklistRepository(db_url=f"sqlite:///{tmp_path / 'notice-checklist.db'}")
    scheduled_start = datetime(2026, 5, 5, 19, 0, tzinfo=UTC)
    record = repo.record_check(
        meeting_id="meeting-123",
        notice_type="regular",
        compliant=True,
        http_status=200,
        warnings=[],
        deadline_at=scheduled_start - timedelta(hours=72),
        posted_at=scheduled_start - timedelta(hours=96),
        minimum_notice_hours=72,
        statutory_basis="72-hour notice rule",
        approved_by="clerk@example.gov",
        actor="clerk@example.gov",
    )

    posted = repo.attach_posting_proof(
        record_id=record.id,
        actor="clerk@example.gov",
        posting_proof={"posted_url": "https://city.example.gov/agendas/123", "location": "City Hall"},
    )

    assert posted is not None
    assert posted.status == NoticeChecklistStatus.POSTED.value
    assert posted.posting_proof == {"posted_url": "https://city.example.gov/agendas/123", "location": "City Hall"}
    assert posted.last_audit_hash != record.last_audit_hash
    assert repo.audit_chain.verify()


async def test_api_notice_checklist_create_list_and_attach_proof(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_NOTICE_CHECKLIST_DB_URL", f"sqlite:///{tmp_path / 'api-notice.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Notice Proof Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = meeting.json()["id"]
        checked = await client.post(
            f"/meetings/{meeting_id}/notice-checklists",
            json={
                "notice_type": "regular",
                "posted_at": "2026-05-01T19:00:00Z",
                "minimum_notice_hours": 72,
                "statutory_basis": "72-hour notice rule",
                "approved_by": "clerk@example.gov",
                "actor": "clerk@example.gov",
            },
        )
        listed = await client.get(f"/meetings/{meeting_id}/notice-checklists")
        proof = await client.post(
            f"/notice-checklists/{checked.json()['id']}/posting-proof",
            json={
                "actor": "clerk@example.gov",
                "posting_proof": {
                    "posted_url": "https://city.example.gov/agendas/123",
                    "location": "City Hall",
                },
            },
        )

    assert checked.status_code == 201
    assert checked.json()["compliant"] is True
    assert len(checked.json()["last_audit_hash"]) == 64
    assert listed.status_code == 200
    assert listed.json()["notice_checklists"][0]["notice_type"] == "regular"
    assert proof.status_code == 200
    assert proof.json()["status"] == "POSTED"
    assert proof.json()["posting_proof"]["location"] == "City Hall"


async def test_api_notice_posting_proof_unknown_record_is_actionable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_NOTICE_CHECKLIST_DB_URL", f"sqlite:///{tmp_path / 'api-notice.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/notice-checklists/missing/posting-proof",
            json={
                "actor": "clerk@example.gov",
                "posting_proof": {"location": "City Hall"},
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"]["fix"] == "Create the notice checklist record before attaching posting proof."
