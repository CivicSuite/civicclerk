"""CivicClerk adapters for the shared CivicCore mock city contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.security import HTTPAuthorizationCredentials

from civiccore.testing.mock_city import (
    MOCK_CITY_CHANGED_SINCE,
    MOCK_CITY_IDP_KEY_ID,
    MOCK_CITY_INTERFACE_STATUS,
    MOCK_CITY_NAME,
    MOCK_CITY_STAFF_ROLES,
    MockCityBackupRetentionCheck,
    MockCityBackupRetentionContract,
    MockCityContractCheck,
    MockCityIdpCheck,
    MockCityIdpContract,
    MockCityVendorContract,
    mock_city_backup_retention_contract,
    mock_city_vendor_contracts,
    run_mock_city_backup_retention_suite,
    run_mock_city_contract_suite,
)

from civicclerk.oidc_auth import (
    OidcStaffAuthConfig,
    authorize_oidc_staff_token,
    oidc_browser_login_config_errors,
    oidc_config_errors,
)


def mock_city_idp_contract() -> MockCityIdpContract:
    """Return CivicClerk's module-specific view of the shared mock IdP contract."""

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
            "Models the authorization-code + PKCE and JWKS/token contract CivicClerk "
            "must satisfy before replacing mock evidence with a real municipal tenant."
        ),
    )


def run_mock_city_idp_contract_suite() -> list[MockCityIdpCheck]:
    """Validate CivicClerk's mock municipal IdP contract without contacting an IdP."""

    contract = mock_city_idp_contract()
    config = _mock_city_oidc_config(contract)
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
        return [
            MockCityIdpCheck(
                provider=contract.provider,
                ok=False,
                message=f"Mock municipal IdP token validation failed: {exc}",
                fix="Align issuer, audience, JWKS, role claims, and allowed staff roles before reuse.",
            )
        ]

    return [
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
    ]


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


__all__ = [
    "MOCK_CITY_CHANGED_SINCE",
    "MOCK_CITY_IDP_KEY_ID",
    "MOCK_CITY_INTERFACE_STATUS",
    "MOCK_CITY_NAME",
    "MOCK_CITY_STAFF_ROLES",
    "MockCityBackupRetentionCheck",
    "MockCityBackupRetentionContract",
    "MockCityContractCheck",
    "MockCityIdpCheck",
    "MockCityIdpContract",
    "MockCityVendorContract",
    "mock_city_backup_retention_contract",
    "mock_city_idp_contract",
    "mock_city_vendor_contracts",
    "run_mock_city_backup_retention_suite",
    "run_mock_city_contract_suite",
    "run_mock_city_idp_contract_suite",
]
