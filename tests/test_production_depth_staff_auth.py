from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import (
    STAFF_AUTH_MODE_ENV_VAR,
    STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR,
    STAFF_AUTH_SSO_PROVIDER_ENV_VAR,
    STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR,
    STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
    STAFF_BEARER_MODE,
    STAFF_TRUSTED_HEADER_MODE,
    app,
)


@pytest.mark.asyncio
async def test_staff_session_reports_open_mode_by_default() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/session")

    assert response.status_code == 200
    assert response.json() == {
        "mode": "open",
        "authenticated": True,
        "roles": ["open_access"],
        "message": "Staff workflow access is running in local open mode.",
        "fix": (
            "Set CIVICCLERK_STAFF_AUTH_MODE=bearer and configure "
            "CIVICCLERK_STAFF_AUTH_TOKEN_ROLES, or switch to "
            "CIVICCLERK_STAFF_AUTH_MODE=trusted_header behind a trusted reverse proxy."
        ),
    }


@pytest.mark.asyncio
async def test_staff_page_discloses_open_and_bearer_modes_without_claiming_sso() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff")

    assert response.status_code == 200
    lowered = response.text.lower()
    assert "local open mode" in lowered
    assert "bearer-protected staff mode" in lowered
    assert "trusted-header staff mode" in lowered
    assert "full oidc login is not shipped yet" in lowered


@pytest.mark.asyncio
async def test_bearer_mode_requires_a_token_for_staff_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE)
    monkeypatch.setenv(STAFF_AUTH_TOKEN_ROLES_ENV_VAR, '{"clerk-token": ["clerk_admin"]}')

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/session")

    assert response.status_code == 401
    assert response.json()["detail"]["message"] == "Bearer token required."
    assert "Authorization header" in response.json()["detail"]["fix"]


@pytest.mark.asyncio
async def test_bearer_mode_rejects_underprivileged_staff_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE)
    monkeypatch.setenv(
        STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
        '{"staff-token": ["archive_reader"], "clerk-token": ["clerk_admin"]}',
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/agenda-intake",
            headers={"Authorization": "Bearer staff-token"},
            json={
                "title": "Staff auth check",
                "department_name": "Clerk",
                "submitted_by": "clerk@example.gov",
                "summary": "Test protected agenda intake.",
                "source_references": [{"label": "Memo", "url": "https://city.example.gov/memo"}],
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"]["required_roles"] == [
        "city_attorney",
        "clerk_admin",
        "clerk_editor",
        "meeting_editor",
    ]
    assert response.json()["detail"]["token_roles"] == ["archive_reader"]


@pytest.mark.asyncio
async def test_bearer_mode_accepts_configured_staff_token_for_session_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE)
    monkeypatch.setenv(
        STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
        '{"clerk-token": ["clerk_admin", "meeting_editor"]}',
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session = await client.get("/staff/session", headers={"Authorization": "Bearer clerk-token"})
        create = await client.post(
            "/agenda-intake",
            headers={"Authorization": "Bearer clerk-token"},
            json={
                "title": "Staff auth check",
                "department_name": "Clerk",
                "submitted_by": "clerk@example.gov",
                "summary": "Test protected agenda intake.",
                "source_references": [{"label": "Memo", "url": "https://city.example.gov/memo"}],
            },
        )

    assert session.status_code == 200
    assert session.json()["mode"] == "bearer"
    assert session.json()["auth_method"] == "bearer"
    assert session.json()["roles"] == ["clerk_admin", "meeting_editor"]
    assert session.json()["token_fingerprint"]
    assert create.status_code == 201
    assert create.json()["title"] == "Staff auth check"


@pytest.mark.asyncio
async def test_trusted_header_mode_requires_proxy_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_TRUSTED_HEADER_MODE)
    monkeypatch.setenv(STAFF_AUTH_SSO_PROVIDER_ENV_VAR, "Entra ID proxy")
    monkeypatch.setenv(STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR, "X-Staff-Email")
    monkeypatch.setenv(STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR, "X-Staff-Roles")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/session")

    assert response.status_code == 401
    assert response.json()["detail"]["message"] == "Trusted identity header missing."
    assert "X-Staff-Email" in response.json()["detail"]["fix"]


@pytest.mark.asyncio
async def test_trusted_header_mode_accepts_proxy_identity_for_session_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_TRUSTED_HEADER_MODE)
    monkeypatch.setenv(STAFF_AUTH_SSO_PROVIDER_ENV_VAR, "Entra ID proxy")
    monkeypatch.setenv(STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR, "X-Staff-Email")
    monkeypatch.setenv(STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR, "X-Staff-Roles")

    headers = {
        "X-Staff-Email": "clerk@example.gov",
        "X-Staff-Roles": "clerk_admin,meeting_editor",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session = await client.get("/staff/session", headers=headers)
        create = await client.post(
            "/agenda-intake",
            headers=headers,
            json={
                "title": "Proxy auth check",
                "department_name": "Clerk",
                "submitted_by": "clerk@example.gov",
                "summary": "Test trusted-header protected agenda intake.",
                "source_references": [{"label": "Memo", "url": "https://city.example.gov/memo"}],
            },
        )

    assert session.status_code == 200
    assert session.json()["mode"] == "trusted_header"
    assert session.json()["auth_method"] == "trusted_header"
    assert session.json()["provider"] == "Entra ID proxy"
    assert session.json()["subject"] == "clerk@example.gov"
    assert session.json()["principal_header"] == "X-Staff-Email"
    assert session.json()["roles_header"] == "X-Staff-Roles"
    assert session.json()["roles"] == ["clerk_admin", "meeting_editor"]
    assert create.status_code == 201
    assert create.json()["title"] == "Proxy auth check"


@pytest.mark.asyncio
async def test_invalid_staff_auth_mode_returns_actionable_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, "mystery")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/agenda-intake",
            json={
                "title": "Staff auth check",
                "department_name": "Clerk",
                "submitted_by": "clerk@example.gov",
                "summary": "Test protected agenda intake.",
                "source_references": [{"label": "Memo", "url": "https://city.example.gov/memo"}],
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "CivicClerk staff auth mode is invalid."
    assert STAFF_AUTH_MODE_ENV_VAR in response.json()["detail"]["fix"]
