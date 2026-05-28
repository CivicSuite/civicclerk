from __future__ import annotations

"""Contract tests for CivicClerk accepting CivicCore suite bearer sessions."""

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE, app


@pytest.mark.asyncio
@pytest.mark.uses_civicclerk_default_staff_mode
async def test_civicclerk_staff_session_accepts_civiccore_suite_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from civiccore.auth.suite_session import issue_suite_session_token

    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE)
    monkeypatch.setenv("CIVICCORE_SUITE_SESSION_SECRET", "clerk-suite-session-secret")
    token = issue_suite_session_token(
        subject="clerk@example.gov",
        roles=frozenset({"clerk_admin", "meeting_editor"}),
        session_id="clerk-suite-session",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get(
            "/staff/session",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["auth_method"] == "civiccore_suite_session"
    assert payload["subject"] == "clerk@example.gov"
    assert payload["roles"] == ["clerk_admin", "meeting_editor"]
