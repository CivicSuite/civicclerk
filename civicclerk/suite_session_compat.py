"""Compatibility bridge for CivicCore suite session bearer tokens."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import tempfile

import jwt


SUITE_SESSION_ENV_VAR = "CIVICCORE_SUITE_SESSION_SECRET"
SUITE_SESSION_REVOCATION_ENV_VAR = "CIVICCORE_SUITE_SESSION_REVOCATION_FILE"
SUITE_SESSION_ALGORITHM = "HS256"
_DEFAULT_TOKEN_TTL = timedelta(minutes=15)
_MAX_LOCAL_REVOCATIONS = 4096
_REVOKED_SESSION_IDS: dict[str, int] = {}


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
    expires = expires_at or now + _DEFAULT_TOKEN_TTL
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
        header = jwt.get_unverified_header(token)
        if header != {"alg": SUITE_SESSION_ALGORITHM, "typ": "JWT"}:
            raise PermissionError("suite session token has an unsupported header")
        claims = jwt.decode(
            token,
            _suite_session_signing_value(),
            algorithms=[SUITE_SESSION_ALGORITHM],
        )
    except PermissionError:
        raise
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
    _load_shared_revocations()
    _prune_revocations()
    if session_id in _REVOKED_SESSION_IDS:
        raise PermissionError("suite session token revoked")

    roles = frozenset(str(role).strip() for role in raw_roles if str(role).strip())
    if roles.isdisjoint(required_roles):
        raise PermissionError("suite session token lacks an allowed role")
    return SuiteSessionPrincipal(subject=subject, roles=roles, session_id=session_id)


def revoke_suite_session(session_id: str) -> None:
    """Revoke a suite session ID in this process."""

    normalized = session_id.strip()
    if normalized:
        _REVOKED_SESSION_IDS[normalized] = int((datetime.now(UTC) + _DEFAULT_TOKEN_TTL).timestamp())
        _prune_revocations()
        _persist_shared_revocations()


def _suite_session_signing_value() -> str:
    value = (os.getenv(SUITE_SESSION_ENV_VAR) or "").strip()
    if not value:
        raise SuiteSessionConfigError(
            f"Set {SUITE_SESSION_ENV_VAR} before issuing or accepting suite session tokens."
        )
    return value


def _revocation_file() -> Path | None:
    raw = (os.getenv(SUITE_SESSION_REVOCATION_ENV_VAR) or "").strip()
    if not raw:
        return None
    return Path(raw)


def _load_shared_revocations() -> None:
    path = _revocation_file()
    if path is None or not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    for session_id, expires_at in data.items():
        if isinstance(session_id, str) and isinstance(expires_at, int):
            _REVOKED_SESSION_IDS[session_id] = expires_at
    _prune_revocations()


def _persist_shared_revocations() -> None:
    path = _revocation_file()
    if path is None:
        return
    _prune_revocations()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(_REVOKED_SESSION_IDS, handle, sort_keys=True)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _prune_revocations() -> None:
    now = int(datetime.now(UTC).timestamp())
    expired = [session_id for session_id, expires_at in _REVOKED_SESSION_IDS.items() if expires_at <= now]
    for session_id in expired:
        _REVOKED_SESSION_IDS.pop(session_id, None)
    if len(_REVOKED_SESSION_IDS) <= _MAX_LOCAL_REVOCATIONS:
        return
    by_expiry = sorted(_REVOKED_SESSION_IDS.items(), key=lambda item: item[1])
    for session_id, _expires_at in by_expiry[: len(_REVOKED_SESSION_IDS) - _MAX_LOCAL_REVOCATIONS]:
        _REVOKED_SESSION_IDS.pop(session_id, None)


__all__ = [
    "SuiteSessionConfigError",
    "SuiteSessionPrincipal",
    "issue_suite_session_token",
    "revoke_suite_session",
    "validate_suite_session_token",
]
