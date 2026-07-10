from __future__ import annotations

"""Real-wire contract tests for CivicMeetings using suite bearer handoff auth."""

import asyncio
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import civicclerk.main as main_module


class RecordingBearerHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, object]] = []

    def do_POST(self) -> None:  # noqa: N802
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.__class__.requests.append(
            {
                "headers": dict(self.headers),
                "json": json.loads(body.decode("utf-8")),
                "path": self.path,
            }
        )
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"event_id":"code-event-suite-bearer"}')

    def log_message(self, format: str, *args: object) -> None:
        return


def test_handoff_wire_uses_suite_bearer_without_spoofable_staff_headers() -> None:
    RecordingBearerHandler.requests = []
    server = HTTPServer(("127.0.0.1", 0), RecordingBearerHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        response = asyncio.run(
            main_module._send_civiccode_handoff_payload(
                intake_url=(
                    f"http://127.0.0.1:{server.server_port}"
                    "/api/v1/civiccode/staff/civicclerk/ordinance-events"
                ),
                auth_value="suite-session-token",
                actor="clerk@example.gov",
                payload={
                    "external_event_id": "handoff-suite-bearer",
                    "civicclerk_meeting_id": "meeting-suite-bearer",
                    "civicclerk_agenda_item_id": "agenda-suite-bearer",
                    "ordinance_number": "2026-042",
                    "title": "Suite bearer ordinance",
                    "status": "adopted",
                    "affected_sections": ["6.12.040"],
                    "source_document_url": "https://city.example.gov/ordinances/2026-042.pdf",
                    "source_document_hash": "sha256:suitebearer",
                    "ordinance_text": "Section 6.12.040 is amended.",
                },
            )
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert response["event_id"] == "code-event-suite-bearer"
    captured = RecordingBearerHandler.requests[0]
    headers = captured["headers"]
    assert headers["Authorization"] == "Bearer suite-session-token"
    assert "X-CivicCode-Role" not in headers
    assert "X-CivicCode-Actor" not in headers
