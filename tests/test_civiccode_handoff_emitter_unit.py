from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

import civicclerk.main as main_module
from civicclerk.main import app


@pytest.fixture(autouse=True)
def clean_handoff_runtime(monkeypatch):
    main_module.meetings = main_module.MeetingStore()
    main_module.motion_votes = main_module.MotionVoteStore()
    main_module.ordinance_resolution_handoffs.clear()
    monkeypatch.delenv(main_module.CIVICCODE_INTAKE_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(main_module.CIVICCODE_INTAKE_AUTH_ENV_VAR, raising=False)
    monkeypatch.delenv(main_module.CIVICCODE_INTAKE_ACTOR_ENV_VAR, raising=False)
    yield
    main_module.ordinance_resolution_handoffs.clear()


def _meeting_and_motion(client: TestClient) -> tuple[str, str]:
    meeting = client.post(
        "/meetings",
        json={
            "title": "Bridge proof meeting",
            "meeting_type": "regular",
            "scheduled_start": "2026-05-23T18:00:00Z",
            "location": "Council Chambers",
        },
    ).json()
    motion = client.post(
        f"/meetings/{meeting['id']}/motions",
        json={
            "text": "Move to adopt ordinance 2026-041.",
            "actor": "clerk@example.gov",
            "agenda_item_id": "agenda-bridge-041",
        },
    ).json()
    return meeting["id"], motion["id"]


def _handoff_payload(motion_id: str) -> dict[str, object]:
    return {
        "item_type": "ordinance",
        "title": "Ordinance 2026-041 amending backyard chicken permits",
        "actor": "clerk@example.gov",
        "legal_reviewer": "attorney@example.gov",
        "text": "An ordinance amending Section 6.12.040 to allow eight backyard chickens with a permit.",
        "source_motion_id": motion_id,
        "ordinance_number": "2026-041",
        "affected_sections": ["6.12.040"],
        "source_document_url": "https://city.example.gov/ordinances/2026-041.pdf",
        "source_document_hash": "sha256:bridgeproof",
        "source_references": [{"agenda_item_id": "agenda-bridge-041"}],
    }


def _configure(monkeypatch):
    monkeypatch.setenv(main_module.CIVICCODE_INTAKE_URL_ENV_VAR, "http://civiccode.test/api/v1/civiccode/staff/civicclerk/ordinance-events")
    monkeypatch.setenv(main_module.CIVICCODE_INTAKE_AUTH_ENV_VAR, "shared-test-value")


def test_handoff_emit_skips_when_unconfigured() -> None:
    client = TestClient(app)
    meeting_id, motion_id = _meeting_and_motion(client)

    response = client.post(
        f"/meetings/{meeting_id}/ordinance-resolution-handoff",
        json=_handoff_payload(motion_id),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["civiccode_handoff_status"] == main_module.CIVICCODE_HANDOFF_UNCONFIGURED
    assert main_module.CIVICCODE_INTAKE_URL_ENV_VAR in payload["civiccode_handoff_last_error"]


def test_handoff_emit_success_records_civiccode_event(monkeypatch) -> None:
    async def fake_send(**kwargs):
        assert kwargs["payload"]["affected_sections"] == ["6.12.040"]
        assert kwargs["auth_value"] == "shared-test-value"
        return {"event_id": "code-event-041"}

    _configure(monkeypatch)
    monkeypatch.setattr(main_module, "_send_civiccode_handoff_payload", fake_send)
    client = TestClient(app)
    meeting_id, motion_id = _meeting_and_motion(client)

    response = client.post(
        f"/meetings/{meeting_id}/ordinance-resolution-handoff",
        json=_handoff_payload(motion_id),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["civiccode_handoff_status"] == main_module.CIVICCODE_HANDOFF_DELIVERED
    assert payload["civiccode_event_id"] == "code-event-041"
    assert payload["civiccode_handoff_last_error"] is None


@pytest.mark.parametrize("status_code", [400, 500])
def test_handoff_emit_http_failure_is_visible(monkeypatch, status_code: int) -> None:
    async def fake_send(**kwargs):
        raise main_module.CivicCodeHandoffEmitError(f"CivicCode intake returned HTTP {status_code}: nope")

    _configure(monkeypatch)
    monkeypatch.setattr(main_module, "_send_civiccode_handoff_payload", fake_send)
    client = TestClient(app)
    meeting_id, motion_id = _meeting_and_motion(client)

    response = client.post(
        f"/meetings/{meeting_id}/ordinance-resolution-handoff",
        json=_handoff_payload(motion_id),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["civiccode_handoff_status"] == main_module.CIVICCODE_HANDOFF_FAILED
    assert f"HTTP {status_code}" in payload["civiccode_handoff_last_error"]


def test_handoff_emit_timeout_is_visible(monkeypatch) -> None:
    async def fake_send(**kwargs):
        raise httpx.ReadTimeout("slow")

    _configure(monkeypatch)
    monkeypatch.setattr(main_module, "_send_civiccode_handoff_payload", fake_send)
    client = TestClient(app)
    meeting_id, motion_id = _meeting_and_motion(client)

    response = client.post(
        f"/meetings/{meeting_id}/ordinance-resolution-handoff",
        json=_handoff_payload(motion_id),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["civiccode_handoff_status"] == main_module.CIVICCODE_HANDOFF_FAILED
    assert "timed out" in payload["civiccode_handoff_last_error"]


def test_manual_retry_promotes_failed_handoff_to_delivered(monkeypatch) -> None:
    attempts = {"count": 0}

    async def fake_send(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise main_module.CivicCodeHandoffEmitError("CivicCode intake returned HTTP 503: warming")
        return {"event_id": "code-event-retry"}

    _configure(monkeypatch)
    monkeypatch.setattr(main_module, "_send_civiccode_handoff_payload", fake_send)
    client = TestClient(app)
    meeting_id, motion_id = _meeting_and_motion(client)
    created = client.post(
        f"/meetings/{meeting_id}/ordinance-resolution-handoff",
        json=_handoff_payload(motion_id),
    ).json()

    retried = client.post(
        f"/meetings/{meeting_id}/ordinance-resolution-handoff/retry",
        json={"handoff_id": created["id"]},
    )

    assert retried.status_code == 200
    record = retried.json()["handoffs"][0]
    assert record["civiccode_handoff_status"] == main_module.CIVICCODE_HANDOFF_DELIVERED
    assert record["civiccode_event_id"] == "code-event-retry"
    assert attempts["count"] == 2
