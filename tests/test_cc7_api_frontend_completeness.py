"""CC-7 API, frontend, auth, and evidence completeness gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import civicclerk.main as main_module
from civicclerk.cc7_completeness import CC7_API_CATEGORIES, CC7_FRONTEND_PAGES, REQUIRED_VIEW_STATES
from civicclerk.main import _is_staff_protected_path, app


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clean_cc7_runtime_state():
    _reset_cc7_runtime_state()
    yield
    _reset_cc7_runtime_state()


def _reset_cc7_runtime_state() -> None:
    main_module.meetings = main_module.MeetingStore()
    main_module.motion_votes = main_module.MotionVoteStore()
    main_module.minutes_drafts = main_module.MinutesDraftStore()
    main_module.public_archive = main_module.PublicArchiveStore()
    main_module.public_comments = main_module.PublicCommentStore()
    main_module.transcript_records.clear()
    main_module.ordinance_resolution_handoffs.clear()
    main_module._agenda_intake_repository = None
    main_module._agenda_intake_db_url = None


def test_new_cc7_api_surfaces_execute_with_actionable_payloads(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "CIVICCLERK_AGENDA_INTAKE_DB_URL",
        f"sqlite+pysqlite:///{(tmp_path / 'agenda-intake.db').as_posix()}",
    )
    main_module._agenda_intake_repository = None
    main_module._agenda_intake_db_url = None
    client = TestClient(app)
    meeting = client.post(
        "/meetings",
        json={
            "title": "CC-7 completeness meeting",
            "meeting_type": "regular",
            "scheduled_start": "2026-05-10T18:00:00Z",
            "location": "Council Chambers",
        },
    ).json()
    meeting_id = meeting["id"]

    staff_report = client.post(
        f"/meetings/{meeting_id}/staff-reports",
        json={
            "title": "Sidewalk repair staff report",
            "department_name": "Public Works",
            "author": "analyst@example.gov",
            "summary": "Explains repair scope and funding source.",
            "source_references": [{"label": "Engineer memo", "url": "https://city.example.gov/memo"}],
            "legal_reviewer": "attorney@example.gov",
        },
    )
    assert staff_report.status_code == 201
    assert "packet citation review" in staff_report.json()["message"]
    listed_reports = client.get(f"/meetings/{meeting_id}/staff-reports").json()["staff_reports"]
    assert listed_reports
    assert listed_reports[0]["legal_reviewer"] == "attorney@example.gov"

    transcript = client.post(
        f"/meetings/{meeting_id}/transcripts",
        json={
            "actor": "clerk@example.gov",
            "source_label": "Clerk notes",
            "transcript_text": "Council discussed the sidewalk repair agenda item.",
        },
    )
    assert transcript.status_code == 201
    assert "review" in transcript.json()["fix"].lower()
    assert client.get(f"/meetings/{meeting_id}/transcripts").json()["transcripts"]

    motion = client.post(
        f"/meetings/{meeting_id}/motions",
        json={"text": "Move to adopt the sidewalk resolution.", "actor": "clerk@example.gov"},
    ).json()
    handoff = client.post(
        f"/meetings/{meeting_id}/ordinance-resolution-handoff",
        json={
            "item_type": "resolution",
            "title": "Sidewalk repair resolution",
            "actor": "clerk@example.gov",
            "legal_reviewer": "attorney@example.gov",
            "text": "Resolution text for legal review.",
            "source_motion_id": motion["id"],
        },
    )
    assert handoff.status_code == 201
    assert "legal/code drafting" in handoff.json()["message"]

    public_record = client.post(
        f"/meetings/{meeting_id}/public-record",
        json={
            "title": "CC-7 public meeting",
            "visibility": "public",
            "posted_agenda": "Agenda text",
            "posted_packet": "Packet text",
            "approved_minutes": "Minutes text",
            "public_comment_enabled": True,
        },
    ).json()
    comment = client.post(
        f"/public/meetings/{public_record['id']}/comments",
        json={"commenter_name": "Resident", "comment": "Please repair Oak Street."},
    )
    assert comment.status_code == 201
    assert client.get("/public-comments/review-queue").json()["total_count"] >= 1

    config = client.get("/admin/config").json()
    prompts = client.get("/admin/prompts").json()
    assert config["api_categories"]
    public_comments_category = next(
        category for category in config["api_categories"] if category["id"] == "public-comments"
    )
    assert "protected staff review queue" in public_comments_category["auth_scope"]
    assert len(prompts["prompts"]) == 9
    assert prompts["fix"].startswith("For public-facing prompt changes")


def test_published_openapi_matches_runtime_schema() -> None:
    published_path = ROOT / "docs" / "api" / "openapi.json"

    assert published_path.exists()
    published = json.loads(published_path.read_text(encoding="utf-8"))
    assert published == app.openapi()


def test_every_cc7_api_category_has_paths_in_published_openapi() -> None:
    paths = set(app.openapi()["paths"])

    for category in CC7_API_CATEGORIES:
        missing = [path for path in category.paths if path not in paths]
        assert not missing, f"{category.id} missing from OpenAPI: {missing}"


def test_protected_cc7_paths_are_behind_staff_auth_middleware() -> None:
    unprotected_prefixes = ("/public",)
    unprotected_exact = {
        "/",
        "/health",
        "/favicon.ico",
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
        "/staff",
        "/staff/auth-readiness",
        "/staff/login",
        "/staff/logout",
        "/staff/oidc/callback",
    }

    for route in app.routes:
        path = getattr(route, "path", "")
        if not path or path in unprotected_exact or path.startswith(unprotected_prefixes):
            continue
        concrete = path.replace("{meeting_id}", "meeting-1").replace("{body_id}", "body-1")
        concrete = concrete.replace("{item_id}", "item-1").replace("{record_id}", "record-1")
        concrete = concrete.replace("{motion_id}", "motion-1").replace("{vote_id}", "vote-1")
        concrete = concrete.replace("{minute_id}", "minute-1").replace("{connector_name}", "granicus")
        concrete = concrete.replace("{source_id}", "source-1").replace("{document_kind}", "agenda")
        assert _is_staff_protected_path(concrete), f"{path} is not covered by staff auth middleware"


def test_staff_auth_enforcement_uses_civiccore_helpers() -> None:
    source = (ROOT / "civicclerk" / "main.py").read_text(encoding="utf-8")

    for helper in (
        "authorize_bearer_roles",
        "authorize_trusted_header_roles",
        "enforce_trusted_proxy_source",
        "resolve_optional_bearer_roles",
    ):
        assert f"from civiccore.auth import" in source
        assert helper in source


def test_react_routes_all_cc7_frontend_pages_and_states() -> None:
    app_tsx = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "SPEC_PAGE_IDS" in app_tsx
    for page in CC7_FRONTEND_PAGES:
        assert f'"{page.id}"' in app_tsx
    for state in REQUIRED_VIEW_STATES:
        assert f'"{state}"' in app_tsx


def test_cc7_browser_evidence_covers_every_page_state_and_viewport() -> None:
    evidence_path = ROOT / "docs" / "browser-qa" / "cc7-api-frontend-completeness-qa-2026-05-06.json"
    summary_path = ROOT / "docs" / "screenshots" / "cc7-api-frontend-completeness-summary.md"

    assert evidence_path.exists()
    assert summary_path.exists()
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    totals = evidence["totals"]
    assert totals["consoleErrors"] == 0
    assert totals["exceptions"] == 0
    assert totals["textCheckFailures"] == 0
    assert totals["keyboardFailures"] == 0
    assert totals["focusFailures"] == 0
    assert totals["horizontalOverflowFailures"] == 0
    assert totals["minContrast"] >= 4.5

    cases = evidence["cases"]
    case_keys = {
        (case["page"], case["state"], case["viewport"])
        for case in cases
    }
    for page in CC7_FRONTEND_PAGES:
        for state in REQUIRED_VIEW_STATES:
            for viewport in ("desktop", "mobile"):
                assert (page.id, state, viewport) in case_keys

    summary = summary_path.read_text(encoding="utf-8").lower()
    for phrase in (
        "cc-7 api and frontend completeness browser qa",
        "20 pages",
        "5 states",
        "desktop",
        "mobile",
        "keyboard failures: 0",
        "focus failures: 0",
        "horizontal overflow failures: 0",
    ):
        assert phrase in summary


def test_openapi_generation_script_is_current() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate-openapi-spec.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Generated docs/api/openapi.json" in result.stdout
    assert json.loads((ROOT / "docs" / "api" / "openapi.json").read_text(encoding="utf-8")) == app.openapi()
