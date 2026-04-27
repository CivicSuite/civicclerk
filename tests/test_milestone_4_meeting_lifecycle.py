from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app

ROOT = Path(__file__).resolve().parents[1]


MEETING_LIFECYCLE = [
    "SCHEDULED",
    "NOTICED",
    "PACKET_POSTED",
    "IN_PROGRESS",
    "RECESSED",
    "ADJOURNED",
    "TRANSCRIPT_READY",
    "MINUTES_DRAFTED",
    "MINUTES_POSTED",
    "MINUTES_ADOPTED",
    "MINUTES_SIGNED",
    "ARCHIVED",
]

VALID_EDGES = set(zip(MEETING_LIFECYCLE[:-1], MEETING_LIFECYCLE[1:], strict=True))
SPECIAL_EDGES = {
    ("IN_PROGRESS", "RECESSED"),
    ("RECESSED", "IN_PROGRESS"),
    ("SCHEDULED", "CANCELLED"),
    ("NOTICED", "CANCELLED"),
}


@pytest.mark.parametrize(("from_status", "to_status"), product(MEETING_LIFECYCLE, repeat=2))
def test_meeting_lifecycle_matrix_allows_only_canonical_edges(
    from_status: str,
    to_status: str,
) -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    result = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status=from_status,
        to_status=to_status,
        actor="clerk@example.gov",
        meeting_type="regular",
        statutory_basis=None,
    )

    if (from_status, to_status) in VALID_EDGES:
        assert result.allowed is True
        assert result.http_status == 200
        assert result.audit_entry["outcome"] == "allowed"
    elif (from_status, to_status) in SPECIAL_EDGES:
        assert result.allowed is True
        assert result.http_status == 200
        assert result.audit_entry["outcome"] == "allowed"
    else:
        assert result.allowed is False
        assert result.http_status == 409
        assert result.audit_entry["outcome"] == "rejected"
        assert result.audit_entry["from_status"] == from_status
        assert result.audit_entry["to_status"] == to_status
        assert "canonical next status" in result.message


@pytest.mark.parametrize("meeting_type", ["emergency", "special"])
def test_emergency_and_special_meetings_require_statutory_basis_for_notice(
    meeting_type: str,
) -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    rejected = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="SCHEDULED",
        to_status="NOTICED",
        actor="clerk@example.gov",
        meeting_type=meeting_type,
        statutory_basis=None,
    )
    assert rejected.allowed is False
    assert rejected.http_status == 422
    assert "statutory basis" in rejected.message.lower()
    assert rejected.audit_entry["outcome"] == "rejected"

    accepted = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="SCHEDULED",
        to_status="NOTICED",
        actor="clerk@example.gov",
        meeting_type=meeting_type,
        statutory_basis="Emergency posting authorized by local open meeting statute.",
    )
    assert accepted.allowed is True
    assert accepted.http_status == 200
    assert accepted.audit_entry["statutory_basis"] == (
        "Emergency posting authorized by local open meeting statute."
    )


@pytest.mark.parametrize("meeting_type", ["Emergency", "SPECIAL"])
def test_emergency_and_special_meeting_type_casing_cannot_bypass_notice_basis(
    meeting_type: str,
) -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    result = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="SCHEDULED",
        to_status="NOTICED",
        actor="clerk@example.gov",
        meeting_type=meeting_type,
        statutory_basis=None,
    )

    assert result.allowed is False
    assert result.http_status == 422
    assert "statutory basis" in result.message.lower()
    assert result.audit_entry["meeting_type"] == meeting_type.lower()


def test_closed_executive_session_requires_statutory_basis_before_in_progress() -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    rejected = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="PACKET_POSTED",
        to_status="IN_PROGRESS",
        actor="clerk@example.gov",
        meeting_type="closed_session",
        statutory_basis=None,
    )
    assert rejected.allowed is False
    assert rejected.http_status == 422
    assert "closed" in rejected.message.lower()
    assert "statutory basis" in rejected.message.lower()

    accepted = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="PACKET_POSTED",
        to_status="IN_PROGRESS",
        actor="clerk@example.gov",
        meeting_type="executive",
        statutory_basis="Personnel matter under state closed-session statute.",
    )
    assert accepted.allowed is True
    assert accepted.audit_entry["statutory_basis"] == (
        "Personnel matter under state closed-session statute."
    )


@pytest.mark.parametrize("meeting_type", ["Closed_Session", "Executive"])
def test_closed_executive_meeting_type_casing_cannot_bypass_session_basis(
    meeting_type: str,
) -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    result = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="PACKET_POSTED",
        to_status="IN_PROGRESS",
        actor="clerk@example.gov",
        meeting_type=meeting_type,
        statutory_basis=None,
    )

    assert result.allowed is False
    assert result.http_status == 422
    assert "statutory basis" in result.message.lower()
    assert result.audit_entry["meeting_type"] == meeting_type.lower()


@pytest.mark.asyncio
async def test_api_valid_meeting_transition_returns_2xx_and_writes_audit_entry() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "City Council Regular Meeting",
                "meeting_type": "regular",
            },
        )
        assert created.status_code == 201
        meeting_id = created.json()["id"]

        transitioned = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
            },
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "NOTICED"

        audit = await client.get(f"/meetings/{meeting_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["entries"][-1] == {
            "meeting_id": meeting_id,
            "actor": "clerk@example.gov",
            "from_status": "SCHEDULED",
            "to_status": "NOTICED",
            "meeting_type": "regular",
            "outcome": "allowed",
            "reason": "transition allowed",
        }


@pytest.mark.asyncio
async def test_api_invalid_meeting_transition_returns_4xx_and_writes_audit_entry() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Planning Commission Special Meeting",
                "meeting_type": "special",
            },
        )
        assert created.status_code == 201
        meeting_id = created.json()["id"]

        rejected = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "IN_PROGRESS",
                "actor": "clerk@example.gov",
            },
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["current_status"] == "SCHEDULED"
        assert rejected.json()["detail"]["requested_status"] == "IN_PROGRESS"

        audit = await client.get(f"/meetings/{meeting_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["entries"][-1]["outcome"] == "rejected"
        assert audit.json()["entries"][-1]["reason"] == "invalid meeting lifecycle transition"


@pytest.mark.asyncio
async def test_api_closed_session_precondition_returns_actionable_422() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Closed Session",
                "meeting_type": "closed_session",
            },
        )
        meeting_id = created.json()["id"]

        await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
                "statutory_basis": "Closed-session notice statute.",
            },
        )
        await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "PACKET_POSTED",
                "actor": "clerk@example.gov",
            },
        )
        rejected = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "IN_PROGRESS",
                "actor": "clerk@example.gov",
            },
        )

        assert rejected.status_code == 422
        assert "statutory basis" in rejected.json()["detail"]["message"].lower()
        current = await client.get(f"/meetings/{meeting_id}")
        assert current.json()["status"] == "PACKET_POSTED"


@pytest.mark.asyncio
async def test_api_meeting_type_casing_cannot_bypass_statutory_basis() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Emergency Meeting",
                "meeting_type": "Emergency",
            },
        )
        assert created.status_code == 201
        meeting_id = created.json()["id"]
        assert created.json()["meeting_type"] == "emergency"

        rejected = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
            },
        )

        assert rejected.status_code == 422
        assert "statutory basis" in rejected.json()["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_api_cancelled_meeting_is_terminal_and_audited() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Cancelled Regular Meeting",
                "meeting_type": "regular",
            },
        )
        meeting_id = created.json()["id"]

        cancelled = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "CANCELLED",
                "actor": "clerk@example.gov",
            },
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"

        rejected = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
            },
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["current_status"] == "CANCELLED"

        audit = await client.get(f"/meetings/{meeting_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["entries"][0]["to_status"] == "CANCELLED"
        assert audit.json()["entries"][0]["outcome"] == "allowed"
        assert audit.json()["entries"][1]["outcome"] == "rejected"


def test_docs_record_meeting_lifecycle_without_claiming_packet_or_minutes_behavior() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        "CHANGELOG.md": (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "meeting lifecycle" in lowered, path
        assert "packet assembly shipped" not in lowered, path
        assert "minutes drafting shipped" not in lowered, path
