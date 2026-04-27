"""Milestone 10 local-first connector/import contract."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app


ROOT = Path(__file__).resolve().parents[1]


CONNECTOR_PAYLOADS = {
    "granicus": {
        "id": "gr-100",
        "name": "Budget Hearing",
        "start": "2026-05-05T19:00:00Z",
        "agenda": [
            {"id": "gr-item-1", "title": "Adopt budget ordinance", "department": "Finance"}
        ],
    },
    "legistar": {
        "MeetingId": "leg-200",
        "MeetingName": "Council Regular Meeting",
        "MeetingDate": "2026-05-06T18:30:00Z",
        "AgendaItems": [
            {"FileNumber": "24-001", "Title": "Approve minutes", "DepartmentName": "Clerk"}
        ],
    },
    "primegov": {
        "meeting_id": "pg-300",
        "title": "Planning Commission",
        "scheduled_start": "2026-05-07T17:00:00Z",
        "items": [
            {"item_id": "pg-item-1", "subject": "Subdivision plat", "owner": "Planning"}
        ],
    },
    "novusagenda": {
        "MeetingGuid": "na-400",
        "MeetingTitle": "Board Work Session",
        "MeetingDateTime": "2026-05-08T16:00:00Z",
        "Agenda": [
            {"Guid": "na-item-1", "Caption": "Capital plan update", "Dept": "Public Works"}
        ],
    },
}


@pytest.mark.parametrize("connector_name", sorted(CONNECTOR_PAYLOADS))
def test_connector_imports_normalize_meeting_payloads_with_source_provenance(
    connector_name: str,
) -> None:
    from civicclerk.connectors import SUPPORTED_CONNECTORS, import_meeting_payload

    assert connector_name in SUPPORTED_CONNECTORS

    result = import_meeting_payload(
        connector_name=connector_name,
        payload=CONNECTOR_PAYLOADS[connector_name],
    )
    public = result.public_dict()

    assert public["connector"] == connector_name
    assert public["source_provenance"] == {
        "connector": connector_name,
        "imported_from": "local_payload",
        "external_meeting_id": public["external_meeting_id"],
    }
    assert public["title"]
    assert public["scheduled_start"].endswith("Z")
    assert len(public["agenda_items"]) == 1
    assert public["agenda_items"][0]["source_provenance"] == {
        "connector": connector_name,
        "imported_from": "local_payload",
        "external_item_id": public["agenda_items"][0]["external_item_id"],
    }


def test_connector_imports_are_local_first_and_do_not_require_outbound_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from civicclerk.connectors import import_meeting_payload

    def blocked_network(*_: object, **__: object) -> None:
        raise AssertionError("connector import attempted outbound network access")

    monkeypatch.setattr(socket, "create_connection", blocked_network)

    result = import_meeting_payload(
        connector_name="granicus",
        payload=CONNECTOR_PAYLOADS["granicus"],
    )

    assert result.title == "Budget Hearing"


def test_connector_import_failures_are_actionable() -> None:
    from civicclerk.connectors import ConnectorImportError, import_meeting_payload

    with pytest.raises(ConnectorImportError) as exc_info:
        import_meeting_payload(
            connector_name="legistar",
            payload={"MeetingId": "leg-200", "AgendaItems": []},
        )

    assert exc_info.value.public_dict() == {
        "message": "Legistar meeting payload is missing required field MeetingName.",
        "fix": "Export the meeting again with MeetingName included, then retry the local import.",
    }


@pytest.mark.asyncio
async def test_api_import_endpoint_accepts_supported_connectors_and_records_provenance() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/imports/granicus/meetings",
            json=CONNECTOR_PAYLOADS["granicus"],
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["connector"] == "granicus"
    assert payload["source_provenance"]["imported_from"] == "local_payload"
    assert payload["agenda_items"][0]["source_provenance"]["connector"] == "granicus"


@pytest.mark.asyncio
async def test_api_import_endpoint_returns_actionable_errors() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        unsupported = await client.post("/imports/unknown/meetings", json={})
        malformed = await client.post(
            "/imports/legistar/meetings",
            json={"MeetingId": "leg-200", "AgendaItems": []},
        )

    assert unsupported.status_code == 404
    assert unsupported.json()["detail"] == {
        "message": "Unsupported connector 'unknown'.",
        "fix": "Use one of: granicus, legistar, novusagenda, primegov.",
    }
    assert malformed.status_code == 422
    assert malformed.json()["detail"]["message"] == (
        "Legistar meeting payload is missing required field MeetingName."
    )


def test_docs_record_connector_import_scope_without_claiming_full_ui_or_live_sync() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    ).lower()

    for connector in ["granicus", "legistar", "primegov", "novusagenda"]:
        assert connector in docs
    assert "local-first" in docs
    assert "source provenance" in docs
    assert "live sync shipped" not in docs
    assert "full ui shipped" not in docs
