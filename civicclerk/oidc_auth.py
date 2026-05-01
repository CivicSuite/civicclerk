"""OIDC bearer-token validation for CivicClerk staff routes."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Iterable

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from civiccore.auth import AuthenticatedPrincipal


@dataclass(frozen=True)
class OidcStaffAuthConfig:
    provider: str
    issuer: str
    audience: str
    jwks_url: str | None
    jwks_json: str | None
    role_claims: tuple[str, ...]
    algorithms: tuple[str, ...]
    authorization_url: str | None
    token_url: str | None
    client_id: str | None
    client_secret: str | None
    redirect_uri: str | None
    session_cookie_secret: str | None


def load_oidc_staff_auth_config(
    *,
    provider_env_var: str,
    issuer_env_var: str,
    audience_env_var: str,
    jwks_url_env_var: str,
    jwks_json_env_var: str,
    role_claims_env_var: str,
    algorithms_env_var: str,
    authorization_url_env_var: str,
    token_url_env_var: str,
    client_id_env_var: str,
    client_secret_env_var: str,
    redirect_uri_env_var: str,
    session_cookie_secret_env_var: str,
) -> OidcStaffAuthConfig:
    """Load the minimal OIDC configuration needed to validate staff access tokens."""

    return OidcStaffAuthConfig(
        provider=os.environ.get(provider_env_var, "OpenID Connect provider").strip()
        or "OpenID Connect provider",
        issuer=os.environ.get(issuer_env_var, "").strip(),
        audience=os.environ.get(audience_env_var, "").strip(),
        jwks_url=os.environ.get(jwks_url_env_var, "").strip() or None,
        jwks_json=os.environ.get(jwks_json_env_var, "").strip() or None,
        role_claims=_split_csv(os.environ.get(role_claims_env_var, "roles,groups")),
        algorithms=_split_csv(os.environ.get(algorithms_env_var, "RS256")),
        authorization_url=os.environ.get(authorization_url_env_var, "").strip() or None,
        token_url=os.environ.get(token_url_env_var, "").strip() or None,
        client_id=os.environ.get(client_id_env_var, "").strip() or None,
        client_secret=os.environ.get(client_secret_env_var, "").strip() or None,
        redirect_uri=os.environ.get(redirect_uri_env_var, "").strip() or None,
        session_cookie_secret=os.environ.get(session_cookie_secret_env_var, "").strip() or None,
    )


def oidc_config_errors(config: OidcStaffAuthConfig) -> list[str]:
    """Return actionable configuration gaps without revealing secret values."""

    errors: list[str] = []
    if not config.issuer or _looks_like_placeholder(config.issuer):
        errors.append("issuer")
    if not config.audience or _looks_like_placeholder(config.audience):
        errors.append("audience")
    if (
        (not config.jwks_url or _looks_like_placeholder(config.jwks_url))
        and (not config.jwks_json or _looks_like_placeholder(config.jwks_json))
    ):
        errors.append("jwks")
    if not config.role_claims:
        errors.append("role_claims")
    if not config.algorithms:
        errors.append("algorithms")
    return errors


def oidc_browser_login_config_errors(config: OidcStaffAuthConfig) -> list[str]:
    """Return missing browser authorization-code flow settings."""

    errors: list[str] = []
    if not config.authorization_url or _looks_like_placeholder(config.authorization_url):
        errors.append("authorization_url")
    if not config.token_url or _looks_like_placeholder(config.token_url):
        errors.append("token_url")
    if not config.client_id or _looks_like_placeholder(config.client_id):
        errors.append("client_id")
    if not config.client_secret or _looks_like_placeholder(config.client_secret):
        errors.append("client_secret")
    if not config.redirect_uri or _looks_like_placeholder(config.redirect_uri):
        errors.append("redirect_uri")
    if not config.session_cookie_secret or _looks_like_placeholder(config.session_cookie_secret):
        errors.append("session_cookie_secret")
    return errors


def authorize_oidc_staff_token(
    credentials: HTTPAuthorizationCredentials | None,
    *,
    config: OidcStaffAuthConfig,
    allowed_roles: Iterable[str],
    env_names: dict[str, str],
) -> AuthenticatedPrincipal:
    """Validate an OIDC access token and require at least one staff role."""

    missing = oidc_config_errors(config)
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "CivicClerk OIDC staff auth is not configured.",
                "fix": _missing_config_fix(missing, env_names),
            },
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "message": "OIDC bearer token required.",
                "fix": (
                    "Send an Authorization header in the form 'Bearer <access token>' "
                    "from the configured municipal identity provider."
                ),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    try:
        signing_key = _resolve_signing_key(token, config)
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=list(config.algorithms),
            audience=config.audience,
            issuer=config.issuer,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "OIDC token has expired.",
                "fix": "Sign in again, refresh the access token, then retry the staff action.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "OIDC token could not be validated.",
                "fix": (
                    "Confirm the issuer, audience, JWKS URL, and token signing algorithm "
                    "match the municipal identity provider."
                ),
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    principal_roles = _extract_roles(claims, config.role_claims)
    normalized_allowed = frozenset(role.strip().lower() for role in allowed_roles if role.strip())
    matching_roles = principal_roles & normalized_allowed
    if not matching_roles:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "OIDC identity lacks an allowed staff role.",
                "fix": (
                    "Map the identity provider app role or group claim to one of the "
                    "CivicClerk staff roles before retrying."
                ),
                "required_roles": sorted(normalized_allowed),
                "principal_roles": sorted(principal_roles),
            },
        )

    subject = _first_string_claim(
        claims,
        ("preferred_username", "email", "upn", "unique_name", "sub"),
    )
    return AuthenticatedPrincipal(
        token_fingerprint=hashlib.sha256(token.encode("utf-8")).hexdigest()[:16],
        roles=frozenset(sorted(matching_roles)),
        auth_method="oidc",
        subject=subject,
        provider=config.provider,
    )


def encode_oidc_staff_session(
    principal: AuthenticatedPrincipal,
    *,
    config: OidcStaffAuthConfig,
    max_age_seconds: int,
) -> str:
    """Create a short-lived signed browser session from an already-validated OIDC identity."""

    if not config.session_cookie_secret:
        raise ValueError("OIDC staff session cookie secret is missing.")
    now = int(time.time())
    expires_at = now + max_age_seconds
    return jwt.encode(
        {
            "iss": "civicclerk-staff-session",
            "aud": "civicclerk-staff-browser",
            "iat": now,
            "exp": expires_at,
            "auth_method": "oidc_browser_session",
            "provider": principal.provider,
            "subject": principal.subject,
            "roles": sorted(principal.roles),
            "oidc_token_fingerprint": principal.token_fingerprint,
        },
        config.session_cookie_secret,
        algorithm="HS256",
    )


def authorize_oidc_staff_session_cookie(
    session_cookie: str | None,
    *,
    config: OidcStaffAuthConfig,
    allowed_roles: Iterable[str],
    env_names: dict[str, str],
) -> AuthenticatedPrincipal:
    """Validate a signed CivicClerk browser session cookie for OIDC staff routes."""

    if not session_cookie:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "OIDC sign-in required.",
                "fix": "Open /staff/login to sign in with the configured municipal identity provider.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not config.session_cookie_secret or _looks_like_placeholder(config.session_cookie_secret):
        raise HTTPException(
            status_code=503,
            detail={
                "message": "OIDC browser session signing is not configured.",
                "fix": f"Set {env_names['session_cookie_secret']} to a strong random value before browser sign-in.",
            },
        )
    try:
        claims = jwt.decode(
            session_cookie,
            config.session_cookie_secret,
            algorithms=["HS256"],
            audience="civicclerk-staff-browser",
            issuer="civicclerk-staff-session",
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "OIDC browser session has expired.",
                "fix": "Open /staff/login and sign in again before retrying the staff action.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "OIDC browser session could not be validated.",
                "fix": "Clear the CivicClerk staff session cookie, sign in again, and confirm the session secret has not changed.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    principal_roles = _extract_roles(claims, ("roles",))
    normalized_allowed = frozenset(role.strip().lower() for role in allowed_roles if role.strip())
    matching_roles = principal_roles & normalized_allowed
    if not matching_roles:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "OIDC browser session lacks an allowed staff role.",
                "fix": "Ask IT to map the identity provider app role or group claim to a CivicClerk staff role, then sign in again.",
                "required_roles": sorted(normalized_allowed),
                "principal_roles": sorted(principal_roles),
            },
        )

    fingerprint_source = str(claims.get("oidc_token_fingerprint") or session_cookie)
    return AuthenticatedPrincipal(
        token_fingerprint=hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:16],
        roles=frozenset(sorted(matching_roles)),
        auth_method="oidc_browser_session",
        subject=_first_string_claim(claims, ("subject", "sub")),
        provider=_first_string_claim(claims, ("provider",)),
    )


def _resolve_signing_key(token: str, config: OidcStaffAuthConfig) -> object:
    if config.jwks_json:
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")
        jwks = json.loads(config.jwks_json)
        keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
        for raw_key in keys:
            if not isinstance(raw_key, dict):
                continue
            if kid and raw_key.get("kid") != kid:
                continue
            return jwt.PyJWK.from_dict(raw_key).key
        raise jwt.InvalidTokenError("No matching OIDC signing key found in configured JWKS JSON.")

    if config.jwks_url is None:
        raise jwt.InvalidTokenError("OIDC JWKS URL is missing.")
    return jwt.PyJWKClient(config.jwks_url).get_signing_key_from_jwt(token).key


def _extract_roles(claims: dict, role_claims: Iterable[str]) -> frozenset[str]:
    roles: set[str] = set()
    for claim_name in role_claims:
        raw_value = claims.get(claim_name)
        if isinstance(raw_value, str):
            roles.update(role.strip().lower() for role in raw_value.split(",") if role.strip())
        elif isinstance(raw_value, list):
            roles.update(str(role).strip().lower() for role in raw_value if str(role).strip())
    return frozenset(roles)


def _first_string_claim(claims: dict, names: Iterable[str]) -> str | None:
    for name in names:
        value = claims.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _split_csv(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw_value.split(",") if part.strip())


def _looks_like_placeholder(value: str | None) -> bool:
    if value is None:
        return False
    lowered = value.lower()
    return "<" in value or ">" in value or "replace-" in lowered or "change-this" in lowered


def _missing_config_fix(missing: Iterable[str], env_names: dict[str, str]) -> str:
    missing = list(missing)
    labels = {
        "issuer": env_names["issuer"],
        "audience": env_names["audience"],
        "jwks": f"{env_names['jwks_url']} or {env_names['jwks_json']}",
        "role_claims": env_names["role_claims"],
        "algorithms": env_names["algorithms"],
    }
    needed = ", ".join(labels[item] for item in missing)
    return f"Set {needed} before exposing CivicClerk staff routes in OIDC mode."
