"""Milestone 13 staff workflow UI foundation contract."""

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
    assert 'aria-label="CivicClerk staff workflow foundation"' in html
    assert "Skip to workflow board" in html
    assert "CivicClerk Staff Workflow Foundation" in html
    assert "v0.1.0" in html
    assert "Full workflow UI screens are still planned" in html
    assert "/agenda-intake" in html
    assert "database-backed staff queue" in html
    assert "/meetings/{id}/packet-assemblies" in html
    assert "packet assembly records" in html
    assert "/meetings/{id}/notice-checklists" in html
    assert "notice checklist records" in html

    for workflow in [
        "Agenda intake",
        "Meeting lifecycle",
        "Packet and notice",
        "Motions, votes, actions",
        "Minutes drafts",
        "Public archive",
        "Connector imports",
    ]:
        assert workflow in html

    for state in ["loading", "success", "empty", "error", "partial"]:
        assert f'data-state="{state}"' in html

    for api_path in [
        "/agenda-intake",
        "/meetings/{id}/packet-snapshots",
        "/meetings/{id}/packet-assemblies",
        "/meetings/{id}/notice-checklists",
        "/meetings/{id}/notices/check",
        "/meetings/{id}/minutes/drafts",
        "/public/archive/search",
        "/imports/{connector}/meetings",
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
    assert "staff workflow UI foundation" in docs
    assert "Full workflow UI screens are still planned" in docs
    assert (ROOT / "docs" / "screenshots" / "milestone13-staff-ui-desktop.png").exists()
    assert (ROOT / "docs" / "screenshots" / "milestone13-staff-ui-mobile.png").exists()


def test_browser_qa_gate_mentions_staff_ui_evidence() -> None:
    script = (ROOT / "scripts" / "verify-browser-qa.py").read_text(encoding="utf-8")

    assert "milestone13-staff-ui-desktop.png" in script
    assert "milestone13-staff-ui-mobile.png" in script
