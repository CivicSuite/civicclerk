from __future__ import annotations

import base64
import json
import urllib.parse
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from civiccore.security import looks_like_placeholder
from httpx import ASGITransport, AsyncClient

from civicclerk.main import (
    STAFF_AUTH_OIDC_AUTHORIZATION_URL_ENV_VAR,
    STAFF_AUTH_OIDC_ALGORITHMS_ENV_VAR,
    STAFF_AUTH_OIDC_AUDIENCE_ENV_VAR,
    STAFF_AUTH_OIDC_CLIENT_ID_ENV_VAR,
    STAFF_AUTH_OIDC_CLIENT_SECRET_ENV_VAR,
    STAFF_AUTH_OIDC_ISSUER_ENV_VAR,
    STAFF_AUTH_OIDC_JWKS_JSON_ENV_VAR,
    STAFF_AUTH_OIDC_JWKS_URL_ENV_VAR,
    STAFF_AUTH_OIDC_PROVIDER_ENV_VAR,
    STAFF_AUTH_OIDC_REDIRECT_URI_ENV_VAR,
    STAFF_AUTH_OIDC_ROLE_CLAIMS_ENV_VAR,
    STAFF_AUTH_OIDC_SESSION_SECRET_ENV_VAR,
    STAFF_AUTH_OIDC_TOKEN_URL_ENV_VAR,
    STAFF_AUTH_MODE_ENV_VAR,
    STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR,
    STAFF_AUTH_SSO_PROVIDER_ENV_VAR,
    STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR,
    STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR,
    STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
    STAFF_BEARER_MODE,
    STAFF_OIDC_PKCE_COOKIE_NAME,
    STAFF_OIDC_MODE,
    STAFF_OIDC_SESSION_COOKIE_NAME,
    STAFF_OIDC_STATE_COOKIE_NAME,
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
            "CIVICCLERK_STAFF_AUTH_TOKEN_ROLES, switch to "
            "CIVICCLERK_STAFF_AUTH_MODE=trusted_header behind a trusted reverse proxy, "
            "or use CIVICCLERK_STAFF_AUTH_MODE=oidc with municipal OIDC settings."
        ),
    }


@pytest.mark.asyncio
async def test_staff_auth_readiness_reports_open_mode_as_rehearsal_only() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/auth-readiness")

    assert response.status_code == 200
    assert response.json()["mode"] == "open"
    assert response.json()["ready"] is True
    assert response.json()["deployment_ready"] is False
    assert response.json()["message"] == (
        "Local open mode is ready for rehearsal, but not for real staff deployment."
    )
    assert STAFF_AUTH_MODE_ENV_VAR in response.json()["fix"]


@pytest.mark.asyncio
async def test_staff_page_discloses_open_and_bearer_modes_without_claiming_sso() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff")

    assert response.status_code == 200
    lowered = response.text.lower()
    assert "local open mode" in lowered
    assert "bearer-protected staff mode" in lowered
    assert "trusted-header staff mode" in lowered
    assert "oidc-protected staff mode" in lowered


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
async def test_bearer_mode_readiness_requires_token_role_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE)
    monkeypatch.delenv(STAFF_AUTH_TOKEN_ROLES_ENV_VAR, raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/auth-readiness")

    assert response.status_code == 200
    assert response.json()["mode"] == "bearer"
    assert response.json()["ready"] is False
    assert response.json()["deployment_ready"] is False
    assert "no staff token mappings are configured yet" in response.json()["message"]
    assert STAFF_AUTH_TOKEN_ROLES_ENV_VAR in response.json()["fix"]
    assert "session_probe" not in response.json()
    assert "write_probe" not in response.json()


@pytest.mark.asyncio
async def test_oidc_mode_readiness_requires_provider_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_OIDC_MODE)
    _clear_oidc_env(monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/auth-readiness")

    assert response.status_code == 200
    assert response.json()["mode"] == "oidc"
    assert response.json()["ready"] is False
    assert response.json()["deployment_ready"] is False
    assert "required provider settings are missing" in response.json()["message"]
    assert STAFF_AUTH_OIDC_ISSUER_ENV_VAR in response.json()["fix"]
    assert STAFF_AUTH_OIDC_AUDIENCE_ENV_VAR in response.json()["fix"]
    assert STAFF_AUTH_OIDC_JWKS_URL_ENV_VAR in response.json()["fix"]
    assert "session_probe" not in response.json()


def test_oidc_placeholder_detection_uses_civiccore_security_helper() -> None:
    assert looks_like_placeholder("<tenant-id>") is True
    assert looks_like_placeholder("replace-with-real-issuer") is True
    assert looks_like_placeholder("https://login.example.gov/brookfield/v2.0") is False


@pytest.mark.asyncio
async def test_oidc_mode_accepts_staff_role_token_for_session_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _configure_oidc(monkeypatch, roles=["clerk_admin", "meeting_editor"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        session = await client.get("/staff/session", headers={"Authorization": f"Bearer {token}"})
        create = await client.post(
            "/agenda-intake",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "OIDC auth check",
                "department_name": "Clerk",
                "submitted_by": "clerk@example.gov",
                "summary": "Test OIDC protected agenda intake.",
                "source_references": [{"label": "Memo", "url": "https://city.example.gov/memo"}],
            },
        )

    assert session.status_code == 200
    assert session.json()["mode"] == "oidc"
    assert session.json()["auth_method"] == "oidc"
    assert session.json()["provider"] == "Brookfield Entra ID"
    assert session.json()["subject"] == "clerk@example.gov"
    assert session.json()["roles"] == ["clerk_admin", "meeting_editor"]
    assert create.status_code == 201
    assert create.json()["title"] == "OIDC auth check"


@pytest.mark.asyncio
async def test_oidc_mode_rejects_underprivileged_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _configure_oidc(monkeypatch, roles=["archive_reader"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/agenda-intake",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "OIDC auth check",
                "department_name": "Clerk",
                "submitted_by": "records@example.gov",
                "summary": "Test OIDC protected agenda intake.",
                "source_references": [{"label": "Memo", "url": "https://city.example.gov/memo"}],
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"]["message"] == "OIDC identity lacks an allowed staff role."
    assert response.json()["detail"]["principal_roles"] == ["archive_reader"]
    assert response.json()["detail"]["required_roles"] == [
        "city_attorney",
        "clerk_admin",
        "clerk_editor",
        "meeting_editor",
    ]


@pytest.mark.asyncio
async def test_oidc_mode_readiness_reports_session_and_write_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_oidc(monkeypatch, roles=["clerk_admin"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/auth-readiness")

    assert response.status_code == 200
    assert response.json()["mode"] == "oidc"
    assert response.json()["ready"] is True
    assert response.json()["deployment_ready"] is True
    assert response.json()["provider"] == "Brookfield Entra ID"
    assert response.json()["issuer"] == "configured"
    assert response.json()["audience"] == "configured"
    assert response.json()["jwks"] == "configured"
    assert response.json()["role_claims"] == ["roles", "groups"]
    assert response.json()["algorithms"] == ["HS256"]
    assert response.json()["browser_login"]["ready"] is False
    assert STAFF_AUTH_OIDC_AUTHORIZATION_URL_ENV_VAR in response.json()["browser_login"]["fix"]
    assert response.json()["session_probe"]["path"] == "/staff/session"
    assert response.json()["session_probe"]["headers"] == {"Authorization": "Bearer <OIDC access token>"}
    assert response.json()["write_probe"]["path"] == "/agenda-intake"
    assert "OIDC-protected staff writes" in response.json()["write_probe"]["body"]["summary"]


@pytest.mark.asyncio
async def test_oidc_login_requires_browser_flow_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_oidc(monkeypatch, roles=["clerk_admin"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/login", follow_redirects=False)

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "OIDC browser sign-in is not fully configured."
    assert STAFF_AUTH_OIDC_AUTHORIZATION_URL_ENV_VAR in response.json()["detail"]["fix"]
    assert STAFF_AUTH_OIDC_SESSION_SECRET_ENV_VAR in response.json()["detail"]["fix"]


@pytest.mark.asyncio
async def test_oidc_login_redirect_sets_state_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_oidc_browser(monkeypatch, roles=["clerk_admin"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://clerk.example.gov") as client:
        response = await client.get("/staff/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith("https://login.example.gov/authorize?")
    parsed = urllib.parse.urlparse(response.headers["location"])
    query = urllib.parse.parse_qs(parsed.query)
    assert query["client_id"] == ["civicclerk-client"]
    assert query["redirect_uri"] == ["https://clerk.example.gov/staff/oidc/callback"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid profile email"]
    assert query["state"][0]
    assert query["code_challenge"][0]
    assert query["code_challenge_method"] == ["S256"]
    assert STAFF_OIDC_STATE_COOKIE_NAME in response.cookies
    assert STAFF_OIDC_PKCE_COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_oidc_callback_sets_browser_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _configure_oidc_browser(monkeypatch, roles=["clerk_admin", "meeting_editor"])

    from civicclerk import main as main_module

    observed: dict[str, str] = {}

    def fake_exchange(code: str, config, *, code_verifier: str) -> dict[str, str]:
        observed["code"] = code
        observed["code_verifier"] = code_verifier
        return {"id_token": token}

    monkeypatch.setattr(main_module, "_exchange_oidc_authorization_code", fake_exchange)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://clerk.example.gov") as client:
        client.cookies.set(STAFF_OIDC_STATE_COOKIE_NAME, "state-123", domain="clerk.example.gov")
        client.cookies.set(STAFF_OIDC_PKCE_COOKIE_NAME, "pkce-verifier-123", domain="clerk.example.gov")
        callback = await client.get(
            "/staff/oidc/callback?code=abc123&state=state-123",
            follow_redirects=False,
        )
        session = await client.get("/staff/session")
        create = await client.post(
            "/agenda-intake",
            json={
                "title": "OIDC browser session auth check",
                "department_name": "Clerk",
                "submitted_by": "clerk@example.gov",
                "summary": "Test OIDC browser-session protected agenda intake.",
                "source_references": [{"label": "Memo", "url": "https://city.example.gov/memo"}],
            },
        )

    assert callback.status_code == 302
    assert callback.headers["location"] == "/staff"
    assert observed == {"code": "abc123", "code_verifier": "pkce-verifier-123"}
    assert STAFF_OIDC_SESSION_COOKIE_NAME in callback.cookies
    assert session.status_code == 200
    assert session.json()["mode"] == "oidc"
    assert session.json()["auth_method"] == "oidc_browser_session"
    assert session.json()["subject"] == "clerk@example.gov"
    assert session.json()["roles"] == ["clerk_admin", "meeting_editor"]
    assert create.status_code == 201
    assert create.json()["title"] == "OIDC browser session auth check"


@pytest.mark.asyncio
async def test_oidc_callback_prefers_access_token_when_id_token_has_client_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    access_token = _configure_oidc_browser(monkeypatch, roles=["clerk_admin"])
    id_token = _make_oidc_token(roles=["clerk_admin"], audience="civicclerk-client")

    from civicclerk import main as main_module

    monkeypatch.setattr(
        main_module,
        "_exchange_oidc_authorization_code",
        lambda code, config, *, code_verifier: {
            "id_token": id_token,
            "access_token": access_token,
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://clerk.example.gov") as client:
        client.cookies.set(STAFF_OIDC_STATE_COOKIE_NAME, "state-123", domain="clerk.example.gov")
        client.cookies.set(STAFF_OIDC_PKCE_COOKIE_NAME, "pkce-verifier-123", domain="clerk.example.gov")
        callback = await client.get(
            "/staff/oidc/callback?code=abc123&state=state-123",
            follow_redirects=False,
        )
        session = await client.get("/staff/session")

    assert callback.status_code == 302
    assert session.status_code == 200
    assert session.json()["auth_method"] == "oidc_browser_session"


@pytest.mark.asyncio
async def test_oidc_callback_rejects_state_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_oidc_browser(monkeypatch, roles=["clerk_admin"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://clerk.example.gov") as client:
        client.cookies.set(STAFF_OIDC_STATE_COOKIE_NAME, "expected-state", domain="clerk.example.gov")
        response = await client.get(
            "/staff/oidc/callback?code=abc123&state=attacker-state",
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "OIDC sign-in state did not match."
    assert "/staff/login" in response.json()["detail"]["fix"]


@pytest.mark.asyncio
async def test_oidc_callback_requires_pkce_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_oidc_browser(monkeypatch, roles=["clerk_admin"])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://clerk.example.gov") as client:
        client.cookies.set(STAFF_OIDC_STATE_COOKIE_NAME, "state-123", domain="clerk.example.gov")
        response = await client.get(
            "/staff/oidc/callback?code=abc123&state=state-123",
            follow_redirects=False,
        )

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "OIDC sign-in PKCE verifier is missing."
    assert "/staff/login" in response.json()["detail"]["fix"]


@pytest.mark.asyncio
async def test_oidc_logout_clears_browser_session_cookie() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://clerk.example.gov") as client:
        response = await client.get("/staff/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/staff"
    assert f"{STAFF_OIDC_SESSION_COOKIE_NAME}=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_trusted_header_mode_requires_proxy_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_TRUSTED_HEADER_MODE)
    monkeypatch.setenv(STAFF_AUTH_SSO_PROVIDER_ENV_VAR, "Entra ID proxy")
    monkeypatch.setenv(STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR, "X-Staff-Email")
    monkeypatch.setenv(STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR, "X-Staff-Roles")
    monkeypatch.setenv(STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR, "127.0.0.1/32")

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
    monkeypatch.setenv(STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR, "10.20.30.0/24")

    headers = {
        "X-Staff-Email": "clerk@example.gov",
        "X-Staff-Roles": "clerk_admin,meeting_editor",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("10.20.30.40", 443)),
        base_url="http://testserver",
    ) as client:
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
async def test_trusted_header_mode_readiness_reports_configured_proxy_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_TRUSTED_HEADER_MODE)
    monkeypatch.setenv(STAFF_AUTH_SSO_PROVIDER_ENV_VAR, "Entra ID proxy")
    monkeypatch.setenv(STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR, "X-Staff-Email")
    monkeypatch.setenv(STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR, "X-Staff-Roles")
    monkeypatch.setenv(STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR, "10.20.30.0/24")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/auth-readiness")

    assert response.status_code == 200
    assert response.json()["mode"] == "trusted_header"
    assert response.json()["ready"] is True
    assert response.json()["deployment_ready"] is True
    assert response.json()["provider"] == "Entra ID proxy"
    assert response.json()["principal_header"] == "X-Staff-Email"
    assert response.json()["roles_header"] == "X-Staff-Roles"
    assert response.json()["trusted_proxy_cidrs"] == ["10.20.30.0/24"]
    assert response.json()["reverse_proxy_reference"]["kind"] == "nginx_trusted_header_bridge"
    assert response.json()["reverse_proxy_reference"]["path"] == "docs/examples/trusted-header-nginx.conf"
    assert response.json()["reverse_proxy_reference"]["headers"] == {
        "X-Staff-Email": "<authenticated staff email>",
        "X-Staff-Roles": "<comma-separated mapped staff roles>",
    }
    assert "Strip any client-supplied copies" in response.json()["reverse_proxy_reference"]["steps"][1]
    assert response.json()["local_proxy_rehearsal"]["scope"] == "loopback_only"
    assert response.json()["local_proxy_rehearsal"]["script_path"] == "scripts/local_trusted_header_proxy.py"
    assert response.json()["local_proxy_rehearsal"]["trusted_proxy_cidrs"] == ["127.0.0.1/32"]
    assert response.json()["local_proxy_rehearsal"]["app_env"][STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR] == "127.0.0.1/32"
    assert response.json()["local_proxy_rehearsal"]["headers"] == {
        "X-Staff-Email": "clerk@example.gov",
        "X-Staff-Roles": "clerk_admin,meeting_editor",
    }
    assert "Run the helper command" in response.json()["local_proxy_rehearsal"]["steps"][1]
    assert "reverse-proxy deployment readiness" in response.json()["message"]
    assert response.json()["session_probe"]["path"] == "/staff/session"
    assert response.json()["session_probe"]["headers"] == {
        "X-Staff-Email": "clerk@example.gov",
        "X-Staff-Roles": "clerk_admin,meeting_editor",
    }
    assert response.json()["write_probe"]["path"] == "/agenda-intake"
    assert response.json()["write_probe"]["headers"] == {
        "X-Staff-Email": "clerk@example.gov",
        "X-Staff-Roles": "clerk_admin,meeting_editor",
    }


@pytest.mark.asyncio
async def test_trusted_header_mode_rejects_underprivileged_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_TRUSTED_HEADER_MODE)
    monkeypatch.setenv(STAFF_AUTH_SSO_PROVIDER_ENV_VAR, "Entra ID proxy")
    monkeypatch.setenv(STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR, "X-Staff-Email")
    monkeypatch.setenv(STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR, "X-Staff-Roles")
    monkeypatch.setenv(STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR, "10.20.30.0/24")

    headers = {
        "X-Staff-Email": "records@example.gov",
        "X-Staff-Roles": "archive_reader",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("10.20.30.40", 443)),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
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

    assert response.status_code == 403
    assert response.json()["detail"]["message"] == "Trusted identity lacks an allowed role."
    assert response.json()["detail"]["required_roles"] == [
        "city_attorney",
        "clerk_admin",
        "clerk_editor",
        "meeting_editor",
    ]
    assert response.json()["detail"]["principal_roles"] == ["archive_reader"]
    assert response.json()["detail"]["principal"] == "records@example.gov"


@pytest.mark.asyncio
async def test_trusted_header_mode_requires_trusted_proxy_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_TRUSTED_HEADER_MODE)
    monkeypatch.setenv(STAFF_AUTH_SSO_PROVIDER_ENV_VAR, "Entra ID proxy")
    monkeypatch.setenv(STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR, "X-Staff-Email")
    monkeypatch.setenv(STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR, "X-Staff-Roles")

    headers = {
        "X-Staff-Email": "clerk@example.gov",
        "X-Staff-Roles": "clerk_admin",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/session", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"]["message"] == "Trusted-header proxy allowlist is missing."
    assert STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR in response.json()["detail"]["fix"]


@pytest.mark.asyncio
async def test_trusted_header_mode_readiness_requires_proxy_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_TRUSTED_HEADER_MODE)
    monkeypatch.setenv(STAFF_AUTH_SSO_PROVIDER_ENV_VAR, "Entra ID proxy")
    monkeypatch.setenv(STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR, "X-Staff-Email")
    monkeypatch.setenv(STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR, "X-Staff-Roles")
    monkeypatch.delenv(STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR, raising=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/auth-readiness")

    assert response.status_code == 200
    assert response.json()["mode"] == "trusted_header"
    assert response.json()["ready"] is False
    assert response.json()["deployment_ready"] is False
    assert "allowlist is missing" in response.json()["message"]
    assert STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR in response.json()["fix"]
    assert "docs/examples/trusted-header-nginx.conf" in response.json()["fix"]
    assert response.json()["reverse_proxy_reference"]["path"] == "docs/examples/trusted-header-nginx.conf"
    assert response.json()["local_proxy_rehearsal"]["script_path"] == "scripts/local_trusted_header_proxy.py"
    assert response.json()["local_proxy_rehearsal"]["proxy_env"]["CIVICCLERK_LOCAL_PROXY_UPSTREAM"] == "http://127.0.0.1:8000"
    assert "localhost rehearsal only" in response.json()["local_proxy_rehearsal"]["warnings"][0]
    assert "session_probe" not in response.json()
    assert "write_probe" not in response.json()


@pytest.mark.asyncio
async def test_bearer_mode_readiness_reports_session_and_write_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_BEARER_MODE)
    monkeypatch.setenv(
        STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
        '{"clerk-token": ["clerk_admin", "meeting_editor"]}',
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/staff/auth-readiness")

    assert response.status_code == 200
    assert response.json()["mode"] == "bearer"
    assert response.json()["ready"] is True
    assert response.json()["deployment_ready"] is True
    assert response.json()["session_probe"] == {
        "method": "GET",
        "path": "/staff/session",
        "headers": {"Authorization": "Bearer <configured token>"},
        "note": "Run this through the same browser, proxy, or API client that will reach protected staff pages.",
    }
    assert response.json()["write_probe"]["method"] == "POST"
    assert response.json()["write_probe"]["path"] == "/agenda-intake"
    assert response.json()["write_probe"]["headers"] == {
        "Authorization": "Bearer <configured token>"
    }


@pytest.mark.asyncio
async def test_trusted_header_mode_rejects_untrusted_proxy_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_TRUSTED_HEADER_MODE)
    monkeypatch.setenv(STAFF_AUTH_SSO_PROVIDER_ENV_VAR, "Entra ID proxy")
    monkeypatch.setenv(STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR, "X-Staff-Email")
    monkeypatch.setenv(STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR, "X-Staff-Roles")
    monkeypatch.setenv(STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR, "10.20.30.0/24")

    headers = {
        "X-Staff-Email": "clerk@example.gov",
        "X-Staff-Roles": "clerk_admin",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app, client=("203.0.113.22", 443)),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/staff/session", headers=headers)

    assert response.status_code == 403
    assert (
        response.json()["detail"]["message"]
        == "Trusted staff headers were not received from an approved proxy."
    )
    assert response.json()["detail"]["client_host"] == "203.0.113.22"
    assert response.json()["detail"]["trusted_proxy_cidrs"] == ["10.20.30.0/24"]
    assert STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR in response.json()["detail"]["fix"]


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


def _clear_oidc_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        STAFF_AUTH_OIDC_PROVIDER_ENV_VAR,
        STAFF_AUTH_OIDC_ISSUER_ENV_VAR,
        STAFF_AUTH_OIDC_AUDIENCE_ENV_VAR,
        STAFF_AUTH_OIDC_JWKS_JSON_ENV_VAR,
        STAFF_AUTH_OIDC_JWKS_URL_ENV_VAR,
        STAFF_AUTH_OIDC_ROLE_CLAIMS_ENV_VAR,
        STAFF_AUTH_OIDC_ALGORITHMS_ENV_VAR,
        STAFF_AUTH_OIDC_AUTHORIZATION_URL_ENV_VAR,
        STAFF_AUTH_OIDC_TOKEN_URL_ENV_VAR,
        STAFF_AUTH_OIDC_CLIENT_ID_ENV_VAR,
        STAFF_AUTH_OIDC_CLIENT_SECRET_ENV_VAR,
        STAFF_AUTH_OIDC_REDIRECT_URI_ENV_VAR,
        STAFF_AUTH_OIDC_SESSION_SECRET_ENV_VAR,
    ):
        monkeypatch.delenv(name, raising=False)


def _configure_oidc(monkeypatch: pytest.MonkeyPatch, *, roles: list[str]) -> str:
    secret = "brookfield-oidc-test-secret-with-32-bytes"
    issuer = "https://login.example.gov/brookfield/v2.0"
    audience = "api://civicclerk"
    key_id = "brookfield-key-1"
    monkeypatch.setenv(STAFF_AUTH_MODE_ENV_VAR, STAFF_OIDC_MODE)
    monkeypatch.setenv(STAFF_AUTH_OIDC_PROVIDER_ENV_VAR, "Brookfield Entra ID")
    monkeypatch.setenv(STAFF_AUTH_OIDC_ISSUER_ENV_VAR, issuer)
    monkeypatch.setenv(STAFF_AUTH_OIDC_AUDIENCE_ENV_VAR, audience)
    monkeypatch.setenv(STAFF_AUTH_OIDC_ROLE_CLAIMS_ENV_VAR, "roles,groups")
    monkeypatch.setenv(STAFF_AUTH_OIDC_ALGORITHMS_ENV_VAR, "HS256")
    monkeypatch.setenv(
        STAFF_AUTH_OIDC_JWKS_JSON_ENV_VAR,
        json.dumps(
            {
                "keys": [
                    {
                        "kty": "oct",
                        "kid": key_id,
                        "k": _base64url(secret.encode("utf-8")),
                        "alg": "HS256",
                    }
                ]
            }
        ),
    )
    return _make_oidc_token(roles=roles, audience=audience)


def _make_oidc_token(*, roles: list[str], audience: str) -> str:
    secret = "brookfield-oidc-test-secret-with-32-bytes"
    issuer = "https://login.example.gov/brookfield/v2.0"
    key_id = "brookfield-key-1"
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "sub": "staff-subject",
            "preferred_username": "clerk@example.gov",
            "roles": roles,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        secret,
        algorithm="HS256",
        headers={"kid": key_id},
    )


def _configure_oidc_browser(monkeypatch: pytest.MonkeyPatch, *, roles: list[str]) -> str:
    token = _configure_oidc(monkeypatch, roles=roles)
    monkeypatch.setenv(STAFF_AUTH_OIDC_AUTHORIZATION_URL_ENV_VAR, "https://login.example.gov/authorize")
    monkeypatch.setenv(STAFF_AUTH_OIDC_TOKEN_URL_ENV_VAR, "https://login.example.gov/token")
    monkeypatch.setenv(STAFF_AUTH_OIDC_CLIENT_ID_ENV_VAR, "civicclerk-client")
    monkeypatch.setenv(STAFF_AUTH_OIDC_CLIENT_SECRET_ENV_VAR, "browser-client-secret")
    monkeypatch.setenv(
        STAFF_AUTH_OIDC_REDIRECT_URI_ENV_VAR,
        "https://clerk.example.gov/staff/oidc/callback",
    )
    monkeypatch.setenv(
        STAFF_AUTH_OIDC_SESSION_SECRET_ENV_VAR,
        "brookfield-session-cookie-secret-with-32-bytes",
    )
    return token


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
