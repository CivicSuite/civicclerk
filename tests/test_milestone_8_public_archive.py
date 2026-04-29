from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app

ROOT = Path(__file__).resolve().parents[1]


async def _create_meeting(client: AsyncClient, title: str, meeting_type: str = "regular") -> str:
    response = await client.post(
        "/meetings",
        json={
            "title": title,
            "meeting_type": meeting_type,
            "scheduled_start": "2026-05-05T19:00:00Z",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _publish_public_record(
    client: AsyncClient,
    *,
    meeting_id: str,
    title: str,
    visibility: str = "public",
    closed_session_notes: str | None = None,
) -> dict:
    response = await client.post(
        f"/meetings/{meeting_id}/public-record",
        json={
            "title": title,
            "visibility": visibility,
            "posted_agenda": "Agenda: approve sidewalk repairs.",
            "posted_packet": "Packet: staff report and fiscal note.",
            "approved_minutes": "Approved minutes: motion passed 5-0.",
            "closed_session_notes": closed_session_notes,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_public_calendar_lists_only_public_records_and_counts_only_public_items() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        public_meeting_id = await _create_meeting(client, "Public Council Meeting")
        closed_meeting_id = await _create_meeting(client, "Closed Litigation Briefing", "closed_session")
        public_record = await _publish_public_record(
            client,
            meeting_id=public_meeting_id,
            title="Public Council Meeting",
        )
        await _publish_public_record(
            client,
            meeting_id=closed_meeting_id,
            title="Closed Litigation Briefing",
            visibility="closed_session",
            closed_session_notes="Privileged litigation strategy for Acme lawsuit.",
        )

        calendar = await client.get("/public/meetings")

    assert calendar.status_code == 200
    payload = calendar.json()
    assert payload["total_count"] == 1
    assert payload["meetings"] == [public_record]
    assert "Closed Litigation" not in str(payload)
    assert "Privileged litigation" not in str(payload)


@pytest.mark.asyncio
async def test_public_detail_never_leaks_closed_session_content_or_existence() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        closed_meeting_id = await _create_meeting(client, "Closed Personnel Review", "closed_session")
        closed_record = await _publish_public_record(
            client,
            meeting_id=closed_meeting_id,
            title="Closed Personnel Review",
            visibility="closed_session",
            closed_session_notes="Employee discipline discussion with names and allegations.",
        )

        detail = await client.get(f"/public/meetings/{closed_record['id']}")

    assert detail.status_code == 404
    assert detail.json()["detail"] == "Public meeting record not found."
    assert "Closed Personnel" not in detail.text
    assert "Employee discipline" not in detail.text
    assert "closed" not in detail.text.lower()


@pytest.mark.asyncio
async def test_anonymous_archive_search_never_leaks_closed_session_in_body_counts_or_suggestions() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        public_meeting_id = await _create_meeting(client, "Budget Meeting")
        closed_meeting_id = await _create_meeting(client, "Closed Cybersecurity Briefing", "closed_session")
        public_record = await _publish_public_record(
            client,
            meeting_id=public_meeting_id,
            title="Budget Meeting",
        )
        await _publish_public_record(
            client,
            meeting_id=closed_meeting_id,
            title="Closed Cybersecurity Briefing",
            visibility="closed_session",
            closed_session_notes="Zero-day vulnerability response plan.",
        )

        public_search = await client.get("/public/archive/search", params={"q": "Budget"})
        closed_search = await client.get("/public/archive/search", params={"q": "Zero-day"})

    assert public_search.status_code == 200
    assert public_search.json()["total_count"] == 1
    assert public_search.json()["results"] == [public_record]
    assert closed_search.status_code == 200
    assert closed_search.json() == {"total_count": 0, "results": [], "suggestions": []}
    assert "Zero-day" not in closed_search.text
    assert "Cybersecurity" not in closed_search.text


@pytest.mark.asyncio
async def test_archive_search_normalizes_case_and_whitespace() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting_id = await _create_meeting(client, "Normalization Budget Meeting")
        public_record = await _publish_public_record(
            client,
            meeting_id=meeting_id,
            title="Normalization Budget Meeting",
        )

        search = await client.get(
            "/public/archive/search",
            params={"q": "  normalization   budget   meeting  "},
        )

    assert search.status_code == 200
    assert search.json()["results"] == [public_record]


@pytest.mark.asyncio
async def test_permission_aware_archive_search_for_staff_roles() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        closed_meeting_id = await _create_meeting(client, "Closed Labor Negotiation", "closed_session")
        await _publish_public_record(
            client,
            meeting_id=closed_meeting_id,
            title="Closed Labor Negotiation",
            visibility="closed_session",
            closed_session_notes="Collective bargaining strategy and salary floor.",
        )

        underprivileged = await client.get(
            "/public/archive/search",
            params={"q": "Collective bargaining"},
            headers={"Authorization": "Bearer staff-token"},
        )
        permitted = await client.get(
            "/public/archive/search",
            params={"q": "Collective bargaining"},
            headers={"Authorization": "Bearer archive-reader-token"},
        )

    assert underprivileged.status_code == 503
    assert underprivileged.json()["detail"]["message"] == "CivicClerk archive search staff access auth is not configured."
    assert "CIVICCLERK_AUTH_TOKEN_ROLES" in underprivileged.json()["detail"]["fix"]
    assert permitted.status_code == 503


@pytest.mark.asyncio
async def test_archive_search_requires_allowed_bearer_role_for_closed_session_visibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CIVICCLERK_AUTH_TOKEN_ROLES",
        '{"staff-token": ["meeting_editor"], "archive-reader-token": ["archive_reader"]}',
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        closed_meeting_id = await _create_meeting(client, "Closed Labor Negotiation", "closed_session")
        closed_record = await _publish_public_record(
            client,
            meeting_id=closed_meeting_id,
            title="Closed Labor Negotiation",
            visibility="closed_session",
            closed_session_notes="Collective bargaining strategy and salary floor.",
        )

        underprivileged = await client.get(
            "/public/archive/search",
            params={"q": "Collective bargaining"},
            headers={"Authorization": "Bearer staff-token"},
        )
        permitted = await client.get(
            "/public/archive/search",
            params={"q": "Collective bargaining"},
            headers={"Authorization": "Bearer archive-reader-token"},
        )

    assert underprivileged.status_code == 403
    assert underprivileged.json()["detail"]["required_roles"] == [
        "archive_reader",
        "city_attorney",
        "clerk_admin",
    ]
    assert underprivileged.json()["detail"]["token_roles"] == ["meeting_editor"]
    assert permitted.status_code == 200
    assert permitted.json()["total_count"] >= 1
    assert any(result["id"] == closed_record["id"] for result in permitted.json()["results"])
    assert "Collective bargaining strategy" in permitted.text


@pytest.mark.asyncio
async def test_publish_public_record_response_does_not_echo_closed_session_notes() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        closed_meeting_id = await _create_meeting(client, "Closed Personnel Review", "closed_session")
        response = await client.post(
            f"/meetings/{closed_meeting_id}/public-record",
            json={
                "title": "Closed Personnel Review",
                "visibility": "closed_session",
                "posted_agenda": "Agenda: personnel review.",
                "posted_packet": "Packet: confidential memo.",
                "approved_minutes": "Approved minutes withheld.",
                "closed_session_notes": "Employee discipline discussion with names and allegations.",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "meeting_id": closed_meeting_id,
        "title": "Closed Personnel Review",
        "posted_agenda": "Agenda: personnel review.",
        "posted_packet": "Packet: confidential memo.",
        "approved_minutes": "Approved minutes withheld.",
    }
    assert "closed_session_notes" not in response.text


def test_docs_record_public_archive_scope_without_claiming_full_ui() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        "CHANGELOG.md": (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "public" in lowered, path
        assert "archive" in lowered, path
        assert "closed-session" in lowered or "closed session" in lowered, path
        assert "full ui shipped" not in lowered, path
