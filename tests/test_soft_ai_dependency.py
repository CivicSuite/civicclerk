from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import civicclerk.main as main_module
from civicclerk.main import app

ROOT = Path(__file__).resolve().parents[1]


def _compose_service(compose: str, service_name: str, next_service: str) -> str:
    return compose.split(f"  {service_name}:", 1)[1].split(f"  {next_service}:", 1)[0]


def _minutes_payload() -> dict[str, object]:
    return {
        "model": "ollama/gemma4",
        "prompt_version": "minutes_draft@0.1.0",
        "human_approver": "clerk@example.gov",
        "source_materials": [
            {
                "source_id": "motion-1",
                "label": "Motion text",
                "text": "Council approved the sidewalk repair packet.",
            },
            {
                "source_id": "vote-1",
                "label": "Vote record",
                "text": "The motion passed 5-0.",
            },
        ],
    }


def test_minutes_generation_payload_uses_runtime_model_and_gemma_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_MODEL", "civicsuite-gemma4-12b-qat:q4_0")
    payload = main_module.MinutesAiAssistCreate(**_minutes_payload())

    request = main_module._minutes_generation_payload(payload)

    assert request["model"] == "civicsuite-gemma4-12b-qat:q4_0"
    assert request["raw"] is True
    assert request["stream"] is False
    assert request["prompt"].startswith("<start_of_turn>user\n")
    assert request["prompt"].endswith("<start_of_turn>model\n")
    assert "Return one concise clerk-reviewed minutes draft paragraph in under 220 words" in request["prompt"]
    assert request["options"]["num_predict"] == 220
    assert request["options"]["num_ctx"] == 3072
    assert request["options"]["stop"] == ["<end_of_turn>", "<start_of_turn>"]


def test_ollama_generate_parser_accepts_installed_runtime_variants() -> None:
    assert (
        main_module._parse_ollama_generate_text(
            '{"model":"civicsuite-gemma4-12b-qat:q4_0","response":"Draft ready.","done":true}'
        )
        == "Draft ready."
    )
    assert (
        main_module._parse_ollama_generate_text(
            '{"message":{"role":"assistant","content":"Minutes draft ready."},"done":true}'
        )
        == "Minutes draft ready."
    )
    assert (
        main_module._parse_ollama_generate_text(
            '94\n{"response":"First ","done":false}\n11\n{"response":"second.","done":true}\n0'
        )
        == "First second."
    )
    assert main_module._parse_ollama_generate_text('{"done":true}') == ""


def test_compose_keeps_api_and_worker_bootable_without_ollama_health_gate() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    api_service = _compose_service(compose, "api", "worker")
    worker_service = _compose_service(compose, "worker", "beat")

    assert "CIVICCLERK_OLLAMA_BASE_URL: http://ollama:11434" in api_service
    assert "CIVICCORE_LLM_PROVIDER: ollama" in api_service
    assert "ollama/ollama:latest" in compose
    for service in (api_service, worker_service):
        assert "postgres:" in service
        assert "redis:" in service
        assert "condition: service_healthy" in service
        assert "ollama:" not in service.split("depends_on:", 1)[1].split("healthcheck:", 1)[0]


@pytest.mark.asyncio
async def test_core_clerk_workflow_passes_with_no_ollama_invoked(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(_: main_module.MinutesAiAssistCreate) -> str:
        raise AssertionError("core workflow must not invoke Ollama")

    monkeypatch.setattr(main_module, "_request_ollama_minutes_text", fail_if_called)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        intake = await client.post(
            "/agenda-intake",
            json={
                "title": "Sidewalk Repair Contract",
                "department_name": "Public Works",
                "submitted_by": "pw@example.gov",
                "summary": "Approve sidewalk repair packet.",
                "source_references": [{"source_id": "staff-report", "label": "Staff Report p. 1"}],
            },
        )
        reviewed = await client.post(
            f"/agenda-intake/{intake.json()['id']}/review",
            json={"reviewer": "clerk@example.gov", "ready": True, "notes": "Complete."},
        )
        promoted = await client.post(
            f"/agenda-intake/{intake.json()['id']}/promote",
            json={"reviewer": "clerk@example.gov", "notes": "Move to agenda."},
        )
        agenda_item_id = promoted.json()["agenda_item"]["id"]
        body = await client.post(
            "/meeting-bodies",
            json={"name": "City Council", "body_type": "council", "is_active": True},
        )
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Regular Council Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
                "body_id": body.json()["id"],
            },
        )
        meeting_id = meeting.json()["id"]
        packet = await client.post(
            f"/meetings/{meeting_id}/packet-assemblies",
            json={
                "title": "Sidewalk Repair Packet",
                "agenda_item_ids": [agenda_item_id],
                "actor": "clerk@example.gov",
                "source_references": [{"source_id": "staff-report", "label": "Staff Report p. 1"}],
                "citations": [{"source_id": "staff-report", "locator": "p. 1", "claim": "Repair scope"}],
            },
        )
        finalized = await client.post(
            f"/packet-assemblies/{packet.json()['id']}/finalize",
            json={"actor": "clerk@example.gov"},
        )
        checklist = await client.post(
            f"/meetings/{meeting_id}/notice-checklists",
            json={
                "notice_type": "regular",
                "posted_at": "2026-05-01T19:00:00Z",
                "minimum_notice_hours": 72,
                "statutory_basis": "Local open meeting law requires 72 hours posted notice.",
                "approved_by": "City Clerk",
                "actor": "clerk@example.gov",
            },
        )
        proof = await client.post(
            f"/notice-checklists/{checklist.json()['id']}/posting-proof",
            json={"actor": "clerk@example.gov", "posting_proof": {"url": "https://city.example.gov/notices/1"}},
        )
        motion = await client.post(
            f"/meetings/{meeting_id}/motions",
            json={
                "text": "Move to approve the sidewalk repair packet.",
                "actor": "clerk@example.gov",
                "agenda_item_id": agenda_item_id,
            },
        )
        vote = await client.post(
            f"/motions/{motion.json()['id']}/votes",
            json={"voter_name": "Council Member Rivera", "vote": "aye", "actor": "clerk@example.gov"},
        )
        action = await client.post(
            f"/meetings/{meeting_id}/action-items",
            json={
                "description": "Prepare contract signature packet.",
                "actor": "clerk@example.gov",
                "assigned_to": "Public Works",
                "source_motion_id": motion.json()["id"],
            },
        )
        manual_minutes = await client.post(
            f"/meetings/{meeting_id}/minutes/drafts",
            json={
                **_minutes_payload(),
                "sentences": [
                    {
                        "text": "Council approved the sidewalk repair packet.",
                        "citations": ["motion-1"],
                    },
                    {
                        "text": "The motion passed 5-0.",
                        "citations": ["vote-1"],
                    },
                ],
            },
        )
        archive = await client.post(
            f"/meetings/{meeting_id}/public-record",
            json={
                "title": "Regular Council Meeting",
                "visibility": "public",
                "posted_agenda": "Agenda: sidewalk repair packet.",
                "posted_packet": "Packet: sidewalk repair scope and contract.",
                "approved_minutes": "Approved minutes: council approved the sidewalk repair packet 5-0.",
                "public_comment_enabled": True,
            },
        )
        search = await client.get("/public/archive/search", params={"q": "sidewalk"})

    for response in (
        intake,
        reviewed,
        promoted,
        body,
        meeting,
        packet,
        finalized,
        checklist,
        proof,
        motion,
        vote,
        action,
        manual_minutes,
        archive,
        search,
    ):
        assert response.status_code in {200, 201}, response.text
    assert manual_minutes.json()["status"] == "DRAFT"
    assert manual_minutes.json()["posted"] is False
    assert search.json()["total_count"] >= 1
    assert any(record["id"] == archive.json()["id"] for record in search.json()["results"])


@pytest.mark.asyncio
async def test_minutes_ai_assist_returns_structured_503_when_ollama_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable(_: main_module.MinutesAiAssistCreate) -> str:
        raise main_module.MinutesAssistUnavailableError("Ollama request timed out.")

    monkeypatch.setattr(main_module, "_request_ollama_minutes_text", unavailable)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "AI Assist Unavailable Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        response = await client.post(
            f"/meetings/{meeting.json()['id']}/minutes/ai-assist",
            json=_minutes_payload(),
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["message"] == "AI assist unavailable; CivicMeetings core workflow is still available."
    assert "Start Ollama" in detail["fix"]
    assert "Manual cited minutes drafting remains available" in detail["fix"]
    assert detail["reason"] == "Ollama request timed out."


@pytest.mark.asyncio
async def test_minutes_ai_assist_with_mock_ollama_creates_guarded_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def generated(_: main_module.MinutesAiAssistCreate) -> str:
        return "Council approved the sidewalk repair packet and the motion passed 5-0."

    monkeypatch.setattr(main_module, "_request_ollama_minutes_text", generated)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "AI Assist Available Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        draft = await client.post(
            f"/meetings/{meeting.json()['id']}/minutes/ai-assist",
            json=_minutes_payload(),
        )
        post_attempt = await client.post(f"/minutes/{draft.json()['id']}/post")

    assert draft.status_code == 201, draft.text
    payload = draft.json()
    assert payload["sentences"][0]["citations"] == ["motion-1", "vote-1"]
    assert payload["provenance"]["model"] == "ollama/gemma4"
    assert payload["adopted"] is False
    assert payload["posted"] is False
    assert post_attempt.status_code == 409
    assert post_attempt.json()["detail"]["message"] == "AI-drafted minutes cannot be posted automatically."
