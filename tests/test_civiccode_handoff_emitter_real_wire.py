from __future__ import annotations

"""Real-wire contract tests for CivicMeetings to CivicCode handoff emission."""

import asyncio
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

import civicclerk.main as main_module


class RecordingHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, object]] = []

    def do_POST(self) -> None:  # noqa: N802
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.__class__.requests.append(
            {
                "method": "POST",
                "path": self.path,
                "headers": dict(self.headers),
                "json": json.loads(body.decode("utf-8")),
                "raw": body,
            }
        )
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"event_id":"code-event-real-wire"}')

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture()
def recording_server() -> str:
    RecordingHandler.requests = []
    server = HTTPServer(("127.0.0.1", 0), RecordingHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/api/v1/civiccode/staff/civicclerk/ordinance-events"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_handoff_emitter_sends_suite_bearer_token_and_schema_payload(
    recording_server: str,
) -> None:
    payload = {
        "external_event_id": "handoff-041",
        "civicclerk_meeting_id": "meeting-041",
        "civicclerk_agenda_item_id": "agenda-041",
        "ordinance_number": "2026-041",
        "title": "Backyard chicken ordinance",
        "status": "adopted",
        "affected_sections": ["6.12.040"],
        "source_document_url": "https://city.example.gov/ordinances/2026-041.pdf",
        "source_document_hash": "sha256:realwire",
        "ordinance_text": "Section 6.12.040 is amended to allow eight backyard chickens.",
    }

    response = asyncio.run(
        main_module._send_civiccode_handoff_payload(
            intake_url=recording_server,
            auth_value="suite-token-real-wire",
            actor="clerk@example.gov",
            payload=payload,
        )
    )

    assert response["event_id"] == "code-event-real-wire"
    assert len(RecordingHandler.requests) == 1
    captured = RecordingHandler.requests[0]
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/civiccode/staff/civicclerk/ordinance-events"
    headers = captured["headers"]
    assert headers["Authorization"] == "Bearer suite-token-real-wire"
    assert headers["X-CivicSuite-Session-Actor"] == "clerk@example.gov"
    assert captured["json"]["affected_sections"] == ["6.12.040"]
    assert captured["json"]["source_document_hash"].startswith("sha256:")
