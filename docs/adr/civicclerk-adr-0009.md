# CivicClerk ADR-0009: Staff OIDC Browser Session Bridge

Status: Accepted

## Context

CC-7 requires protected staff API enforcement to go through CivicCore-shipped
helpers when those helpers exist. CivicCore v1.0 ships bearer-token,
trusted-header, trusted-proxy-source, optional bearer role, and trusted-header
configuration helpers. It does not yet ship a browser authorization-code +
PKCE session-cookie helper for CivicClerk's staff shell.

## Decision

CivicClerk keeps the OIDC browser-login/session-cookie bridge in
`civicclerk.oidc_auth` for this release window. API access-token validation,
bearer staff access, trusted-header staff access, trusted proxy-source
enforcement, and archive-search optional bearer authorization continue to use
CivicCore helpers. The module-local browser-session code is documented as an
extraction candidate and is surfaced in `/admin/config`.

## Threat Model Note

The local bridge must treat the browser cookie as a signed staff session, not as
stored raw OIDC tokens. PKCE state and verifier cookies are short-lived and
HttpOnly. Shared deployments must configure issuer, audience, JWKS, role
claims, algorithms, authorization URL, token URL, client settings, redirect URI,
and session-cookie secret before enabling OIDC mode.

## Extraction Plan

When CivicCore ships a reusable browser-session helper, CivicClerk will replace
`civicclerk.oidc_auth` with that helper, keep the `/staff/login`,
`/staff/oidc/callback`, `/staff/logout`, and `/staff/session` HTTP contracts,
and preserve compatibility tests for OIDC token validation, browser login
readiness, session cookie acceptance, logout clearing, and protected write
smoke probes.
