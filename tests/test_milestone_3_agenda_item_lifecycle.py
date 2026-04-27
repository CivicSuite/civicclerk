from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app

ROOT = Path(__file__).resolve().parents[1]


AGENDA_ITEM_LIFECYCLE = [
    "DRAFTED",
    "SUBMITTED",
    "DEPT_APPROVED",
    "LEGAL_REVIEWED",
    "CLERK_ACCEPTED",
    "ON_AGENDA",
    "IN_PACKET",
    "POSTED",
    "HEARD",
    "DISPOSED",
    "ARCHIVED",
]

VALID_EDGES = set(zip(AGENDA_ITEM_LIFECYCLE[:-1], AGENDA_ITEM_LIFECYCLE[1:], strict=True))


@pytest.mark.parametrize(("from_status", "to_status"), product(AGENDA_ITEM_LIFECYCLE, repeat=2))
def test_agenda_item_lifecycle_matrix_allows_only_canonical_edges(
    from_status: str,
    to_status: str,
) -> None:
    from civicclerk.agenda_lifecycle import validate_agenda_item_transition

    result = validate_agenda_item_transition(
        agenda_item_id="agenda-123",
        from_status=from_status,
        to_status=to_status,
        actor="clerk@example.gov",
    )

    if (from_status, to_status) in VALID_EDGES:
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


@pytest.mark.asyncio
async def test_api_valid_transition_returns_2xx_and_writes_audit_entry() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/agenda-items",
            json={
                "title": "Adopt safe streets resolution",
                "department_name": "Public Works",
            },
        )
        assert created.status_code == 201
        item_id = created.json()["id"]

        transitioned = await client.post(
            f"/agenda-items/{item_id}/transitions",
            json={
                "to_status": "SUBMITTED",
                "actor": "clerk@example.gov",
            },
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "SUBMITTED"

        audit = await client.get(f"/agenda-items/{item_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["entries"][-1] == {
            "agenda_item_id": item_id,
            "actor": "clerk@example.gov",
            "from_status": "DRAFTED",
            "to_status": "SUBMITTED",
            "outcome": "allowed",
            "reason": "transition allowed",
        }


@pytest.mark.asyncio
async def test_api_invalid_transition_returns_4xx_and_writes_audit_entry() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/agenda-items",
            json={
                "title": "Approve zoning text amendment",
                "department_name": "Planning",
            },
        )
        assert created.status_code == 201
        item_id = created.json()["id"]

        rejected = await client.post(
            f"/agenda-items/{item_id}/transitions",
            json={
                "to_status": "POSTED",
                "actor": "clerk@example.gov",
            },
        )
        assert rejected.status_code == 409
        payload = rejected.json()
        assert payload["detail"]["current_status"] == "DRAFTED"
        assert payload["detail"]["requested_status"] == "POSTED"
        assert "Next valid status is SUBMITTED" in payload["detail"]["message"]

        audit = await client.get(f"/agenda-items/{item_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["entries"][-1] == {
            "agenda_item_id": item_id,
            "actor": "clerk@example.gov",
            "from_status": "DRAFTED",
            "to_status": "POSTED",
            "outcome": "rejected",
            "reason": "invalid agenda item lifecycle transition",
        }


@pytest.mark.asyncio
async def test_api_unknown_status_returns_actionable_422_without_state_change() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/agenda-items",
            json={
                "title": "Set fee schedule hearing",
                "department_name": "Finance",
            },
        )
        item_id = created.json()["id"]

        rejected = await client.post(
            f"/agenda-items/{item_id}/transitions",
            json={
                "to_status": "READY_FOR_COUNCIL",
                "actor": "clerk@example.gov",
            },
        )

        assert rejected.status_code == 422
        assert "Use one of" in rejected.json()["detail"]["message"]
        audit = await client.get(f"/agenda-items/{item_id}/audit")
        assert audit.json()["entries"][-1]["outcome"] == "rejected"
        current = await client.get(f"/agenda-items/{item_id}")
        assert current.json()["status"] == "DRAFTED"


def test_docs_record_agenda_lifecycle_without_claiming_full_meeting_workflows() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        "CHANGELOG.md": (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "agenda item lifecycle" in lowered, path
        assert "full meeting workflows are implemented" not in lowered, path
        assert "meeting lifecycle enforcement shipped" not in lowered, path
