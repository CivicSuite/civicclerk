"""Reusable mock city integration contracts for CivicSuite modules."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.security import HTTPAuthorizationCredentials

from civicclerk.connectors import SUPPORTED_CONNECTORS, import_meeting_payload
from civicclerk.oidc_auth import (
    OidcStaffAuthConfig,
    authorize_oidc_staff_token,
    oidc_browser_login_config_errors,
    oidc_config_errors,
)
from civicclerk.vendor_delta import plan_vendor_delta_request


MOCK_CITY_STAFF_ROLES = frozenset({"clerk_admin", "meeting_editor", "city_attorney"})
MOCK_CITY_IDP_KEY_ID = "brookfield-mock-idp-key-1"


@dataclass(frozen=True)
class MockCityVendorContract:
    connector: str
    vendor_name: str
    interface_status: str
    method: str
    path: str
    auth_method: str
    delta_query_param: str
    sample_payload: dict[str, Any]
    notes: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "connector": self.connector,
            "vendor_name": self.vendor_name,
            "interface_status": self.interface_status,
            "method": self.method,
            "path": self.path,
            "auth_method": self.auth_method,
            "delta_query_param": self.delta_query_param,
            "sample_payload": self.sample_payload,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MockCityIdpContract:
    provider: str
    interface_status: str
    issuer: str
    audience: str
    authorization_url: str
    token_url: str
    jwks_path: str
    role_claims: tuple[str, ...]
    algorithms: tuple[str, ...]
    client_id: str
    redirect_uri: str
    staff_subject: str
    staff_email: str
    staff_roles: tuple[str, ...]
    notes: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "interface_status": self.interface_status,
            "issuer": self.issuer,
            "audience": self.audience,
            "authorization_url": self.authorization_url,
            "token_url": self.token_url,
            "jwks_path": self.jwks_path,
            "role_claims": list(self.role_claims),
            "algorithms": list(self.algorithms),
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "staff_subject": self.staff_subject,
            "staff_email": self.staff_email,
            "staff_roles": list(self.staff_roles),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MockCityContractCheck:
    connector: str
    ok: bool
    message: str
    fix: str
    normalized_external_meeting_id: str | None = None
    delta_request_url: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "connector": self.connector,
            "ok": self.ok,
            "message": self.message,
            "fix": self.fix,
            "normalized_external_meeting_id": self.normalized_external_meeting_id,
            "delta_request_url": self.delta_request_url,
        }


@dataclass(frozen=True)
class MockCityIdpCheck:
    provider: str
    ok: bool
    message: str
    fix: str
    auth_method: str | None = None
    subject: str | None = None
    roles: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "ok": self.ok,
            "message": self.message,
            "fix": self.fix,
            "auth_method": self.auth_method,
            "subject": self.subject,
            "roles": list(self.roles),
        }


MOCK_CITY_NAME = "City of Brookfield"
MOCK_CITY_CHANGED_SINCE = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
MOCK_CITY_INTERFACE_STATUS = {
    "public-reference",
    "vendor-gated-contract",
}


def mock_city_vendor_contracts() -> list[MockCityVendorContract]:
    """Return reusable vendor contracts for mock-city integration tests."""

    return [
        MockCityVendorContract(
            connector="legistar",
            vendor_name="Legistar",
            interface_status="public-reference",
            method="GET",
            path="/v1/{Client}/Events?EventItems=true",
            auth_method="bearer_token",
            delta_query_param="LastModifiedDate",
            sample_payload={
                "MeetingId": "leg-brookfield-100",
                "MeetingName": "Brookfield City Council Regular Meeting",
                "MeetingDate": "2026-05-06T18:30:00Z",
                "AgendaItems": [
                    {"FileNumber": "24-001", "Title": "Approve minutes", "DepartmentName": "Clerk"},
                    {"FileNumber": "24-002", "Title": "Adopt sidewalk repair resolution", "DepartmentName": "Public Works"},
                ],
            },
            notes=(
                "Legistar exposes a public Web API help surface with Events routes. "
                "Tenant-specific client names and credentials still come from the city/vendor account."
            ),
        ),
        MockCityVendorContract(
            connector="granicus",
            vendor_name="Granicus",
            interface_status="vendor-gated-contract",
            method="GET",
            path="/api/meetings",
            auth_method="api_key",
            delta_query_param="modifiedSince",
            sample_payload={
                "id": "gr-brookfield-100",
                "name": "Brookfield City Council Work Session",
                "start": "2026-05-07T19:00:00Z",
                "agenda": [
                    {"id": "gr-item-1", "title": "Review capital plan", "department": "Finance"},
                ],
            },
            notes=(
                "Public marketing confirms Granicus meeting-management products, but customer API details are account-gated. "
                "This fixture tests CivicSuite's normalized contract until city credentials provide a concrete endpoint."
            ),
        ),
        MockCityVendorContract(
            connector="primegov",
            vendor_name="PrimeGov",
            interface_status="vendor-gated-contract",
            method="GET",
            path="/api/meetings",
            auth_method="bearer_token",
            delta_query_param="updated_since",
            sample_payload={
                "meeting_id": "pg-brookfield-100",
                "title": "Planning Commission",
                "scheduled_start": "2026-05-08T01:00:00Z",
                "items": [
                    {"item_id": "pg-item-1", "subject": "Conditional use permit", "owner": "Planning"},
                ],
            },
            notes="PrimeGov tenant APIs are treated as vendor-gated until a city provides interface documentation.",
        ),
        MockCityVendorContract(
            connector="novusagenda",
            vendor_name="NovusAGENDA",
            interface_status="vendor-gated-contract",
            method="GET",
            path="/api/meetings",
            auth_method="api_key",
            delta_query_param="modifiedSince",
            sample_payload={
                "MeetingGuid": "nov-brookfield-100",
                "MeetingTitle": "Parks Board",
                "MeetingDateTime": "2026-05-09T17:00:00Z",
                "Agenda": [
                    {"Guid": "nov-item-1", "Caption": "Trail maintenance grant", "Dept": "Parks"},
                ],
            },
            notes="NovusAGENDA tenant APIs are treated as vendor-gated until a city provides interface documentation.",
        ),
    ]


def mock_city_idp_contract() -> MockCityIdpContract:
    """Return the reusable no-network municipal IdP contract for protected staff auth."""

    return MockCityIdpContract(
        provider="Brookfield Entra ID",
        interface_status="mock-municipal-idp",
        issuer="https://login.mock-city.example.gov/brookfield/v2.0",
        audience="api://civicclerk",
        authorization_url="https://login.mock-city.example.gov/brookfield/oauth2/v2.0/authorize",
        token_url="https://login.mock-city.example.gov/brookfield/oauth2/v2.0/token",
        jwks_path="/brookfield/discovery/v2.0/keys",
        role_claims=("roles", "groups"),
        algorithms=("RS256",),
        client_id="civicclerk-staff-dashboard",
        redirect_uri="https://civicclerk.mock-city.example.gov/staff/oidc/callback",
        staff_subject="brookfield-clerk-001",
        staff_email="clerk@brookfield.example.gov",
        staff_roles=("clerk_admin", "meeting_editor"),
        notes=(
            "Models the authorization-code + PKCE and JWKS/token contract CivicSuite modules "
            "must satisfy before replacing mock evidence with a real municipal tenant."
        ),
    )


def run_mock_city_contract_suite(*, base_url: str = "https://mock-city.example.gov") -> list[MockCityContractCheck]:
    """Validate mock city payloads and delta URLs without contacting vendors."""

    checks: list[MockCityContractCheck] = []
    for contract in mock_city_vendor_contracts():
        if contract.connector not in SUPPORTED_CONNECTORS:
            checks.append(
                MockCityContractCheck(
                    connector=contract.connector,
                    ok=False,
                    message=f"{contract.vendor_name} is not on the shared connector allowlist.",
                    fix="Add the connector to CivicCore before adding module-level mock-city tests.",
                )
            )
            continue
        if contract.interface_status not in MOCK_CITY_INTERFACE_STATUS:
            checks.append(
                MockCityContractCheck(
                    connector=contract.connector,
                    ok=False,
                    message=f"{contract.vendor_name} has an unknown interface status.",
                    fix="Use public-reference or vendor-gated-contract so test evidence stays honest.",
                )
            )
            continue
        try:
            normalized = import_meeting_payload(
                connector_name=contract.connector,
                payload=contract.sample_payload,
            ).public_dict()
            delta_plan = plan_vendor_delta_request(
                connector=contract.connector,
                source_url=f"{base_url}{contract.path.replace('{Client}', 'brookfield')}",
                changed_since=MOCK_CITY_CHANGED_SINCE,
            )
        except Exception as exc:  # pragma: no cover - defensive safety net for CLI output.
            checks.append(
                MockCityContractCheck(
                    connector=contract.connector,
                    ok=False,
                    message=f"{contract.vendor_name} mock city contract failed: {exc}",
                    fix="Update the mock payload or connector adapter before reusing this suite.",
                )
            )
            continue
        checks.append(
            MockCityContractCheck(
                connector=contract.connector,
                ok=True,
                message=(
                    f"{contract.vendor_name} mock city contract normalized "
                    f"{normalized['external_meeting_id']} and planned a delta request."
                ),
                fix="Reuse this contract in module integration tests; replace only the module-specific assertions.",
                normalized_external_meeting_id=normalized["external_meeting_id"],
                delta_request_url=delta_plan.request_url,
            )
        )
    return checks


def run_mock_city_idp_contract_suite() -> list[MockCityIdpCheck]:
    """Validate the mock municipal IdP contract without contacting an IdP."""

    contract = mock_city_idp_contract()
    config = _mock_city_oidc_config(contract)
    checks: list[MockCityIdpCheck] = []
    config_gaps = oidc_config_errors(config)
    browser_gaps = oidc_browser_login_config_errors(config)
    if config_gaps or browser_gaps:
        missing = ", ".join(config_gaps + browser_gaps)
        return [
            MockCityIdpCheck(
                provider=contract.provider,
                ok=False,
                message=f"Mock municipal IdP contract is missing required settings: {missing}.",
                fix="Update the mock IdP contract before reusing it in module protected-auth tests.",
            )
        ]

    try:
        token = _mock_city_staff_token(contract)
        principal = authorize_oidc_staff_token(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            config=config,
            allowed_roles=MOCK_CITY_STAFF_ROLES,
            env_names={
                "issuer": "CIVICCLERK_STAFF_OIDC_ISSUER",
                "audience": "CIVICCLERK_STAFF_OIDC_AUDIENCE",
                "jwks_url": "CIVICCLERK_STAFF_OIDC_JWKS_URL",
                "jwks_json": "CIVICCLERK_STAFF_OIDC_JWKS_JSON",
                "role_claims": "CIVICCLERK_STAFF_OIDC_ROLE_CLAIMS",
                "algorithms": "CIVICCLERK_STAFF_OIDC_ALGORITHMS",
            },
        )
    except Exception as exc:  # pragma: no cover - defensive CLI reporting.
        checks.append(
            MockCityIdpCheck(
                provider=contract.provider,
                ok=False,
                message=f"Mock municipal IdP token validation failed: {exc}",
                fix="Align issuer, audience, JWKS, role claims, and allowed staff roles before reuse.",
            )
        )
    else:
        checks.append(
            MockCityIdpCheck(
                provider=contract.provider,
                ok=True,
                message=(
                    f"{contract.provider} mock OIDC contract validated "
                    f"{principal.subject} with staff roles."
                ),
                fix="Reuse this IdP contract in module protected-auth tests; replace only module-specific staff actions.",
                auth_method=principal.auth_method,
                subject=principal.subject,
                roles=tuple(sorted(principal.roles)),
            )
        )
    return checks


def _mock_city_oidc_config(contract: MockCityIdpContract) -> OidcStaffAuthConfig:
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_mock_city_private_key().public_key()))
    public_jwk.update({"kid": MOCK_CITY_IDP_KEY_ID, "alg": "RS256", "use": "sig"})
    jwks_json = json.dumps({"keys": [public_jwk]})
    return OidcStaffAuthConfig(
        provider=contract.provider,
        issuer=contract.issuer,
        audience=contract.audience,
        jwks_url=f"https://login.mock-city.example.gov{contract.jwks_path}",
        jwks_json=jwks_json,
        role_claims=contract.role_claims,
        algorithms=contract.algorithms,
        authorization_url=contract.authorization_url,
        token_url=contract.token_url,
        client_id=contract.client_id,
        client_secret="mock-client-secret-not-reported",
        redirect_uri=contract.redirect_uri,
        session_cookie_secret="mock-session-secret-not-reported-and-long",
    )


def _mock_city_staff_token(contract: MockCityIdpContract) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": contract.issuer,
            "aud": contract.audience,
            "sub": contract.staff_subject,
            "preferred_username": contract.staff_email,
            "roles": list(contract.staff_roles),
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        _mock_city_private_key(),
        algorithm="RS256",
        headers={"kid": MOCK_CITY_IDP_KEY_ID},
    )


@lru_cache(maxsize=1)
def _mock_city_private_key() -> rsa.RSAPrivateKey:
    """Generate one in-memory keypair per process for offline IdP contract validation."""

    return rsa.generate_private_key(public_exponent=65537, key_size=2048)
