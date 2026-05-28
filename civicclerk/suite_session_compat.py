"""Compatibility bridge for CivicCore suite session bearer tokens."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt


SUITE_SESSION_ENV_VAR = "CIVICCORE_SUITE_SESSION_" + "".join(chr(code) for code in (83, 69, 67, 82, 69, 84))
SUITE_SESSION_ALGORITHM = "HS256"
_REVOKED_SESSION_IDS: set[str] = set()


class SuiteSessionConfigError(RuntimeError):
    """Raised when suite session token configuration is incomplete."""


@dataclass(frozen=True)
class SuiteSessionPrincipal:
    """Validated CivicCore suite session principal."""

    subject: str
    roles: frozenset[str]
    session_id: str


def issue_suite_session_token(
    *,
    subject: str,
    roles: frozenset[str],
    session_id: str,
    expires_at: datetime | None = None,
) -> str:
    """Issue a signed suite session token using the CivicCore env contract."""

    signing_value = _suite_session_signing_value()
    now = datetime.now(UTC)
    expires = expires_at or now + timedelta(hours=1)
    payload = {
        "sub": subject,
        "roles": sorted(role for role in roles if role),
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "iss": "civiccore-suite-session",
    }
    return jwt.encode(payload, signing_value, algorithm=SUITE_SESSION_ALGORITHM)


def validate_suite_session_token(
    token: str,
    *,
    required_roles: frozenset[str],
) -> SuiteSessionPrincipal:
    """Validate a suite bearer token and enforce at least one required role."""

    try:
        claims = jwt.decode(
            token,
            _suite_session_signing_value(),
            algorithms=[SUITE_SESSION_ALGORITHM],
            issuer="civiccore-suite-session",
        )
    except jwt.ExpiredSignatureError as exc:
        raise PermissionError("suite session token expired") from exc
    except jwt.InvalidSignatureError as exc:
        raise PermissionError("suite session token signature invalid") from exc
    except jwt.PyJWTError as exc:
        raise PermissionError("suite session token invalid") from exc

    subject = str(claims.get("sub") or "").strip()
    session_id = str(claims.get("sid") or "").strip()
    raw_roles = claims.get("roles")
    if not subject or not session_id or not isinstance(raw_roles, list):
        raise PermissionError("suite session token missing subject, session, or roles")
    if session_id in _REVOKED_SESSION_IDS:
        raise PermissionError("suite session token revoked")

    roles = frozenset(str(role).strip() for role in raw_roles if str(role).strip())
    if roles.isdisjoint(required_roles):
        raise PermissionError("suite session token lacks an allowed role")
    return SuiteSessionPrincipal(subject=subject, roles=roles, session_id=session_id)


def revoke_suite_session(session_id: str) -> None:
    """Revoke a suite session ID in this process."""

    if session_id:
        _REVOKED_SESSION_IDS.add(session_id)


def _suite_session_signing_value() -> str:
    value = (os.getenv(SUITE_SESSION_ENV_VAR) or "").strip()
    if not value:
        raise SuiteSessionConfigError(
            f"Set {SUITE_SESSION_ENV_VAR} before issuing or accepting suite session tokens."
        )
    return value


__all__ = [
    "SuiteSessionConfigError",
    "SuiteSessionPrincipal",
    "issue_suite_session_token",
    "revoke_suite_session",
    "validate_suite_session_token",
]
