"""Public portal shell contract."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE, app


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_public_portal_renders_accessible_resident_shell() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/public")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text

    assert "<main" in html
    assert 'aria-label="CivicClerk public portal shell"' in html
    assert "Skip to public meeting records" in html
    assert "CivicClerk Public Portal" in html
    assert "v0.1.14 API-direct public portal fallback" in html
    assert "Docker/nginx product path" in html
    assert "/public/meetings" in html
    assert "/public/meetings/{id}" in html
    assert "/public/archive/search" in html
    assert 'id="calendar-state"' in html
    assert 'id="meeting-records"' in html
    assert 'id="detail-state"' in html
    assert 'id="record-detail"' in html
    assert 'id="search-form"' in html
    assert 'id="search-state"' in html
    assert 'id="search-results"' in html
    assert "Closed-session content is not displayed here." in html
    assert "Results exclude restricted records for anonymous visitors." in html

    for state in ["loading", "success", "empty", "error", "partial"]:
        assert f'data-state="{state}"' in html

    for fix_path in [
        "refresh the page and confirm the API is running",
        "Staff should publish a public record from /staff",
        "try a broader term or ask the clerk",
        "Confirm the API is running at /public/archive/search",
    ]:
        assert fix_path in html


@pytest.mark.asyncio
async def test_public_portal_stays_public_when_staff_mode_is_protected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        portal = await client.get("/public")
        calendar = await client.get("/public/meetings")

    assert portal.status_code == 200
    assert "CivicClerk Public Portal" in portal.text
    assert calendar.status_code == 200


def test_public_portal_docs_and_browser_evidence_are_current() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "README.txt").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    )

    assert "/public" in docs
    assert "resident-facing React public portal" in docs
    assert "restricted-session" in docs
    assert "closed-session" in docs or "closed session" in docs
    assert (ROOT / "docs" / "screenshots" / "public-portal-shell-desktop.png").exists()
    assert (ROOT / "docs" / "screenshots" / "public-portal-shell-mobile.png").exists()
    assert (ROOT / "docs" / "screenshots" / "public-portal-shell-summary.md").exists()
