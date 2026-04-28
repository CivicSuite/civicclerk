"""Milestone 13 staff workflow screen contract."""

from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from civicclerk.main import app


ROOT = Path(__file__).resolve().parents[1]


async def test_staff_ui_endpoint_renders_accessible_workflow_foundation() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text

    assert "<main" in html
    assert 'aria-label="CivicClerk staff workflow screens"' in html
    assert "Skip to workflow screens" in html
    assert "CivicClerk Staff Workflow Screens" in html
    assert "v0.1.0" in html
    assert "first browser-visible staff workflow screens" in html
    assert "without claiming the full end-to-end clerk console is finished" in html
    assert "/agenda-intake" in html
    assert "Department submission queue" in html
    assert "/meetings/{id}/packet-assemblies" in html
    assert "Packet Assembly" in html
    assert "/meetings/{id}/notice-checklists" in html
    assert "Notice Checklist" in html
    assert "/notice-checklists/{id}/posting-proof" in html
    assert "Live agenda intake action" in html
    assert 'id="agenda-intake-form"' in html
    assert 'id="agenda-review-form"' in html
    assert 'id="agenda-intake-output"' in html
    assert "Submit intake item" in html
    assert "Record readiness review" in html
    assert "Live packet assembly action" in html
    assert 'id="packet-assembly-form"' in html
    assert "Create and finalize packet" in html
    assert "Live notice checklist action" in html
    assert 'id="notice-checklist-form"' in html
    assert "Check notice and attach proof" in html
    assert "Meeting Outcomes" in html
    assert "Motions, votes, and actions" in html
    assert "/meetings/{id}/motions" in html
    assert "/meetings/{id}/action-items" in html
    assert "Live meeting outcomes action" in html
    assert 'id="meeting-outcomes-form"' in html
    assert 'id="meeting-outcomes-output"' in html
    assert "Capture motion, vote, and action" in html
    assert "Minutes Draft" in html
    assert "Citations + provenance" in html
    assert "/meetings/{id}/minutes/drafts" in html
    assert "Live minutes draft action" in html
    assert 'id="minutes-draft-form"' in html
    assert 'id="minutes-draft-output"' in html
    assert "Create cited minutes draft" in html
    assert "URLSearchParams(window.location.search)" in html
    assert "Public Archive" in html
    assert "Public-safe records" in html
    assert "/meetings/{id}/public-record" in html
    assert "/public/archive/search" in html
    assert "Live public archive action" in html
    assert 'id="public-archive-form"' in html
    assert 'id="public-archive-output"' in html
    assert "Publish public archive record" in html
    assert "Connector Import" in html
    assert "Local export payloads" in html
    assert "/imports/{connector}/meetings" in html
    assert "Live connector import action" in html
    assert 'id="connector-import-form"' in html
    assert 'id="connector-import-output"' in html
    assert "Import local connector payload" in html

    for workflow in [
        "Agenda Intake",
        "Packet Assembly",
        "Notice Checklist",
        "Meeting Outcomes",
        "Minutes Draft",
        "Public Archive",
        "Connector Import",
    ]:
        assert workflow in html

    for panel in [
        "screen-intake",
        "screen-packet",
        "screen-notice",
        "screen-outcomes",
        "screen-minutes",
        "screen-archive",
        "screen-imports",
    ]:
        assert f'id="{panel}"' in html

    for state in ["loading", "success", "empty", "error", "partial"]:
        assert f'data-state="{state}"' in html

    for api_path in [
        "/agenda-intake",
        "/agenda-intake/{id}/review",
        "CIVICCLERK_AGENDA_INTAKE_DB_URL",
        "/meetings/{id}/packet-assemblies",
        "/packet-assemblies/{id}/finalize",
        "/meetings/{id}/notice-checklists",
        "/notice-checklists/{id}/posting-proof",
        "/meetings/{id}/motions",
        "/motions/${motion.id}/votes",
        "/meetings/{id}/action-items",
        "/meetings/{id}/minutes/drafts",
        "minutes_draft@0.1.0",
        "/meetings/{id}/public-record",
        "/public/meetings",
        "/public/archive/search",
        "/imports/{connector}/meetings",
        "Granicus",
        "Legistar",
        "PrimeGov",
        "NovusAGENDA",
    ]:
        assert api_path in html


def test_staff_ui_has_current_facing_docs_and_browser_qa_evidence() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    )

    assert "/staff" in docs
    assert "staff workflow screens" in docs
    assert (ROOT / "docs" / "screenshots" / "milestone13-staff-ui-desktop.png").exists()
    assert (ROOT / "docs" / "screenshots" / "milestone13-staff-ui-mobile.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-meeting-outcomes-screen-desktop.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-meeting-outcomes-screen-mobile.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-meeting-outcomes-screen-summary.md").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-minutes-draft-screen-desktop.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-minutes-draft-screen-mobile.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-minutes-draft-screen-summary.md").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-archive-screen-desktop.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-archive-screen-mobile.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-archive-screen-summary.md").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-connector-import-screen-desktop.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-connector-import-screen-mobile.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-connector-import-screen-summary.md").exists()


def test_browser_qa_gate_mentions_staff_ui_evidence() -> None:
    script = (ROOT / "scripts" / "verify-browser-qa.py").read_text(encoding="utf-8")

    assert "milestone13-staff-ui-desktop.png" in script
    assert "milestone13-staff-ui-mobile.png" in script
    assert "browser-qa-production-depth-live-meeting-outcomes-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-meeting-outcomes-screen-mobile.png" in script
    assert "browser-qa-production-depth-live-minutes-draft-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-minutes-draft-screen-mobile.png" in script
    assert "browser-qa-production-depth-live-archive-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-archive-screen-mobile.png" in script
    assert "browser-qa-production-depth-live-connector-import-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-connector-import-screen-mobile.png" in script
