"""Milestone 13 staff workflow screen contract."""

from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from civicclerk.main import app


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.18"


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
    assert "Product cockpit" in html
    assert "Today's clerk desk" in html
    assert "This is the shift from foundation to product" in html
    assert "Items ready for clerk review" in html
    assert "Department submission queue" in html
    assert "Live workflow actions" in html
    assert "Silent dead ends" in html
    assert "Go-live checks" in html
    assert "1. Intake" in html
    assert "2. Build" in html
    assert "3. Publish" in html
    assert f"v{VERSION}" in html
    assert "browser-visible staff workflow screens" in html
    assert "bearer-protected staff mode" in html
    assert "trusted-header staff mode" in html
    assert "OIDC-protected staff mode" in html
    assert "OIDC mode accepts municipal identity-provider access tokens" in html
    assert 'id="staff-auth-token"' in html
    assert 'id="staff-auth-status"' in html
    assert "/staff/auth-readiness" in html
    assert "deployment-ready staff auth contract" in html
    assert "Session probe" in html
    assert "Write probe" in html
    assert "Trusted proxy reference" in html
    assert "docs/examples/trusted-header-nginx.conf" in html
    assert "Local proxy rehearsal" in html
    assert "scripts/local_trusted_header_proxy.py" in html
    assert "127.0.0.1/32" in html
    assert "/staff/session" in html
    assert "CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER" in html
    assert "CIVICCLERK_STAFF_SSO_ROLES_HEADER" in html
    assert "CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES" in html
    assert "/agenda-intake" in html
    assert "Department submission queue" in html
    assert "/meetings/{id}/packet-assemblies" in html
    assert "Packet Assembly" in html
    assert "No packet assemblies yet" in html
    assert "Create a meeting, submit at least one source and citation, then create the packet assembly record." in html
    assert "/meetings/{id}/notice-checklists" in html
    assert "Notice Checklist" in html
    assert "No notice checklist records yet" in html
    assert "Create a meeting, run the notice checklist, then attach posting proof when posted." in html
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
    assert "Live packet export action" in html
    assert 'id="packet-export-form"' in html
    assert 'id="packet-export-output"' in html
    assert "Create packet export bundle" in html
    assert "/meetings/{id}/export-bundle" in html
    assert "Live notice checklist action" in html
    assert 'id="notice-checklist-form"' in html
    assert "Check notice and attach proof" in html
    assert "Meeting Outcomes" in html
    assert "Motions, votes, and actions" in html
    assert "No meeting outcomes captured yet" in html
    assert "Create a meeting, capture a motion, record a vote, and create any follow-up action item." in html
    assert "/meetings/{id}/motions" in html
    assert "/meetings/{id}/action-items" in html
    assert "Live meeting outcomes action" in html
    assert 'id="meeting-outcomes-form"' in html
    assert 'id="meeting-outcomes-output"' in html
    assert "Capture motion, vote, and action" in html
    assert "Minutes Draft" in html
    assert "Citations + provenance" in html
    assert "No minutes drafts created yet" in html
    assert "Create a citation-gated draft after motions, votes, and source materials are ready." in html
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
        "/meetings/{id}/packet-snapshots",
        "/meetings/{id}/export-bundle",
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


async def test_staff_product_cockpit_uses_live_agenda_intake_counts(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_AGENDA_INTAKE_DB_URL", f"sqlite:///{tmp_path / 'staff-cockpit.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        ready_item = await client.post(
            "/agenda-intake",
            json={
                "title": "Approve <script>paving</script> contract",
                "department_name": "Public Works",
                "submitted_by": "pw@example.gov",
                "summary": "Contract award for arterial paving.",
                "source_references": [{"source_id": "staff-report", "title": "Staff report"}],
            },
        )
        revision_item = await client.post(
            "/agenda-intake",
            json={
                "title": "Adopt fee schedule",
                "department_name": "Finance",
                "submitted_by": "finance@example.gov",
                "summary": "Annual fee schedule update.",
                "source_references": [{"source_id": "fee-table", "title": "Fee table"}],
            },
        )
        await client.post(
            f"/agenda-intake/{ready_item.json()['id']}/review",
            json={"reviewer": "clerk@example.gov", "ready": True, "notes": "Complete for packet."},
        )
        await client.post(
            f"/agenda-intake/{revision_item.json()['id']}/review",
            json={"reviewer": "clerk@example.gov", "ready": False, "notes": "Missing attachment."},
        )
        response = await client.get("/staff")

    assert response.status_code == 200
    assert "Live agenda intake queue reports 1 ready, 0 pending, and 1 needing revision." in response.text
    assert "Items ready for clerk review" in response.text
    assert "Approve &lt;script&gt;paving&lt;/script&gt; contract" in response.text
    assert "Approve <script>paving</script> contract" not in response.text
    assert "Request missing information before packet assembly." in response.text


async def test_staff_product_cockpit_handles_unavailable_intake_store(monkeypatch) -> None:
    monkeypatch.setenv("CIVICCLERK_AGENDA_INTAKE_DB_URL", "sqlite:///Z:/missing/civicclerk.db")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff")

    assert response.status_code == 200
    assert "Agenda intake queue is unavailable" in response.text
    assert "check CIVICCLERK_AGENDA_INTAKE_DB_URL" in response.text
    assert "reload the staff desk" in response.text
    assert "Check CIVICCLERK_AGENDA_INTAKE_DB_URL and database reachability" in response.text


async def test_staff_packet_panel_uses_live_packet_assembly_rows(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_PACKET_ASSEMBLY_DB_URL", f"sqlite:///{tmp_path / 'staff-packets.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Live Packet Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        created = await client.post(
            f"/meetings/{meeting.json()['id']}/packet-assemblies",
            json={
                "title": "Packet <script>draft</script>",
                "agenda_item_ids": ["item-1"],
                "actor": "clerk@example.gov",
                "source_references": [{"source_id": "staff-report", "title": "Staff report"}],
                "citations": [{"source_id": "staff-report", "locator": "p. 4", "claim": "Budget"}],
            },
        )
        await client.post(
            f"/packet-assemblies/{created.json()['id']}/finalize",
            json={"actor": "clerk@example.gov"},
        )
        response = await client.get("/staff")

    assert response.status_code == 200
    assert "Packet &lt;script&gt;draft&lt;/script&gt;" in response.text
    assert "Packet <script>draft</script>" not in response.text
    assert "FINALIZED" in response.text
    assert "Create the records-ready packet export bundle." in response.text


async def test_staff_packet_panel_handles_unavailable_packet_store(monkeypatch) -> None:
    monkeypatch.setenv("CIVICCLERK_PACKET_ASSEMBLY_DB_URL", "sqlite:///Z:/missing/packet-assembly.db")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff")

    assert response.status_code == 200
    assert "Packet assembly store unavailable" in response.text
    assert "Check CIVICCLERK_PACKET_ASSEMBLY_DB_URL and database reachability" in response.text


async def test_staff_notice_panel_uses_live_notice_rows(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_NOTICE_CHECKLIST_DB_URL", f"sqlite:///{tmp_path / 'staff-notices.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Live Notice Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        checked = await client.post(
            f"/meetings/{meeting.json()['id']}/notice-checklists",
            json={
                "notice_type": "special",
                "posted_at": "2026-05-01T19:00:00Z",
                "minimum_notice_hours": 24,
                "statutory_basis": "24-hour notice rule",
                "approved_by": "clerk@example.gov",
                "actor": "clerk@example.gov",
            },
        )
        await client.post(
            f"/notice-checklists/{checked.json()['id']}/posting-proof",
            json={"actor": "clerk@example.gov", "posting_proof": {"location": "City Hall"}},
        )
        response = await client.get("/staff")

    assert response.status_code == 200
    assert "special notice" in response.text
    assert "POSTED" in response.text
    assert "Posting proof is attached; keep the record with the meeting packet." in response.text


async def test_staff_notice_panel_handles_unavailable_notice_store(monkeypatch) -> None:
    monkeypatch.setenv("CIVICCLERK_NOTICE_CHECKLIST_DB_URL", "sqlite:///Z:/missing/notice-checklist.db")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff")

    assert response.status_code == 200
    assert "Notice checklist store unavailable" in response.text
    assert "Check CIVICCLERK_NOTICE_CHECKLIST_DB_URL and database reachability" in response.text


async def test_staff_meeting_outcomes_panel_uses_live_outcome_rows() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Live Outcomes Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        motion = await client.post(
            f"/meetings/{meeting.json()['id']}/motions",
            json={
                "text": "Approve <script>street repairs</script>",
                "actor": "clerk@example.gov",
            },
        )
        await client.post(
            f"/motions/{motion.json()['id']}/votes",
            json={"voter_name": "Council Member Rivera", "vote": "aye", "actor": "clerk@example.gov"},
        )
        await client.post(
            f"/meetings/{meeting.json()['id']}/action-items",
            json={
                "description": "Schedule contractor notice.",
                "assigned_to": "Public Works",
                "actor": "clerk@example.gov",
                "source_motion_id": motion.json()["id"],
            },
        )
        response = await client.get("/staff")

    assert response.status_code == 200
    assert "Approve &lt;script&gt;street repairs&lt;/script&gt;" in response.text
    assert "Approve <script>street repairs</script>" not in response.text
    assert "CAPTURED" in response.text
    assert "Vote recorded; action item open." in response.text


async def test_staff_minutes_panel_uses_live_minutes_rows() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Live Minutes Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        created = await client.post(
            f"/meetings/{meeting.json()['id']}/minutes/drafts",
            json={
                "model": "gemma-local",
                "prompt_version": "minutes_draft@0.1.0",
                "human_approver": "clerk@example.gov",
                "source_materials": [
                    {
                        "source_id": "motion-1",
                        "label": "Motion text",
                        "text": "Approve <script>sidewalk</script> repair packet.",
                    }
                ],
                "sentences": [
                    {
                        "text": "Council approved the sidewalk repair packet.",
                        "citations": ["motion-1"],
                    }
                ],
            },
        )
        response = await client.get("/staff")

    assert created.status_code == 201
    assert response.status_code == 200
    assert "clerk@example.gov" in response.text
    assert f"Meeting {meeting.json()['id']} minutes draft" in response.text
    assert "DRAFT" in response.text
    assert "Human review must approve the cited draft before public posting." in response.text


async def test_favicon_is_public_and_empty() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/favicon.ico")

    assert response.status_code == 204
    assert response.text == ""


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
    assert "local_proxy_rehearsal" in docs
    assert "scripts/local_trusted_header_proxy.py" in docs
    assert "127.0.0.1/32" in docs
    assert (ROOT / "docs" / "screenshots" / "milestone13-staff-ui-desktop.png").exists()
    assert (ROOT / "docs" / "screenshots" / "milestone13-staff-ui-mobile.png").exists()
    assert (ROOT / "docs" / "screenshots" / "milestone13-staff-ui-summary.md").exists()
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
    assert (ROOT / "docs" / "browser-qa-production-depth-live-packet-export-screen-desktop.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-packet-export-screen-mobile.png").exists()
    assert (ROOT / "docs" / "browser-qa-production-depth-live-packet-export-screen-summary.md").exists()


def test_local_trusted_header_proxy_helper_is_shipped() -> None:
    helper = ROOT / "scripts" / "local_trusted_header_proxy.py"

    assert helper.exists()
    text = helper.read_text(encoding="utf-8")
    assert "Loopback-only trusted-header proxy rehearsal helper for CivicClerk." in text
    assert "CIVICCLERK_LOCAL_PROXY_UPSTREAM" in text
    assert "X-Forwarded-For" not in text


def test_trusted_proxy_reference_config_is_shipped() -> None:
    config = ROOT / "docs" / "examples" / "trusted-header-nginx.conf"

    assert config.exists()
    text = config.read_text(encoding="utf-8")
    assert "proxy_set_header X-Staff-Email \"\";" in text
    assert "proxy_set_header X-Staff-Roles \"\";" in text
    assert "proxy_pass http://127.0.0.1:8776;" in text


def test_browser_qa_gate_mentions_staff_ui_evidence() -> None:
    script = (ROOT / "scripts" / "verify-browser-qa.py").read_text(encoding="utf-8")

    assert "milestone13-staff-ui-desktop.png" in script
    assert "milestone13-staff-ui-mobile.png" in script
    assert "milestone13-staff-ui-summary.md" in script
    assert "local proxy" in script.lower()
    assert "browser-qa-production-depth-live-meeting-outcomes-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-meeting-outcomes-screen-mobile.png" in script
    assert "browser-qa-production-depth-live-minutes-draft-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-minutes-draft-screen-mobile.png" in script
    assert "browser-qa-production-depth-live-archive-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-archive-screen-mobile.png" in script
    assert "browser-qa-production-depth-live-connector-import-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-connector-import-screen-mobile.png" in script
    assert "browser-qa-production-depth-live-packet-export-screen-desktop.png" in script
    assert "browser-qa-production-depth-live-packet-export-screen-mobile.png" in script
