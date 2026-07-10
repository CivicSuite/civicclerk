"""CivicMeetings adapters for the shared CivicCore mock city contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, Literal

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
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
from civicclerk.connectors import ConnectorImportError, import_meeting_payload


HostileArea = Literal["idp", "vendor", "backup_retention"]


@dataclass(frozen=True)
class MockCityHostileFixture:
    """Secret-free adversarial fixture for the mock-city hostile-mode toggle."""

    area: HostileArea
    scenario: str
    target: str
    trigger: str
    expected_behavior: str
    fix: str
    sample: dict[str, Any]

    def public_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "scenario": self.scenario,
            "target": self.target,
            "trigger": self.trigger,
            "expected_behavior": self.expected_behavior,
            "fix": self.fix,
            "sample": self.sample,
        }


@dataclass(frozen=True)
class MockCityHostileCheck:
    """Conformance result for a hostile-mode mock-city fixture."""

    area: HostileArea
    scenario: str
    target: str
    ok: bool
    message: str
    fix: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "scenario": self.scenario,
            "target": self.target,
            "ok": self.ok,
            "message": self.message,
            "fix": self.fix,
        }


def mock_city_idp_contract() -> MockCityIdpContract:
    """Return CivicMeetings' module-specific view of the shared mock IdP contract."""

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
            "Models the authorization-code + PKCE and JWKS/token contract CivicMeetings "
            "must satisfy before replacing mock evidence with a real municipal tenant."
        ),
    )


def mock_city_idp_hostile_fixtures() -> list[MockCityHostileFixture]:
    """Return hostile IdP protocol cases for Entra, Okta, and Keycloak-style tenants."""

    return [
        MockCityHostileFixture(
            area="idp",
            scenario="expired_access_token",
            target="Brookfield Entra ID",
            trigger="access token exp is in the past",
            expected_behavior="reject with 401 and instruct staff to sign in or refresh before retrying",
            fix="Sign in again or refresh the access token, then retry the staff action.",
            sample={"provider_family": "entra", "claim": "exp", "expected_status": 401},
        ),
        MockCityHostileFixture(
            area="idp",
            scenario="group_claim_only",
            target="Brookfield Okta",
            trigger="staff role is supplied through groups instead of roles",
            expected_behavior="accept the token when the configured group claim maps to a staff role",
            fix="Map the Okta group claim to an allowed CivicMeetings staff role before deployment.",
            sample={"provider_family": "okta", "claim": "groups", "expected_status": 200},
        ),
        MockCityHostileFixture(
            area="idp",
            scenario="jwks_rotation",
            target="Brookfield Keycloak",
            trigger="token kid points at a signing key that is not yet in the configured JWKS",
            expected_behavior="reject with 401 and instruct IT to refresh JWKS or align signing keys",
            fix="Refresh the JWKS cache or update the configured JWKS JSON before retrying staff access.",
            sample={"provider_family": "keycloak", "claim": "kid", "expected_status": 401},
        ),
        MockCityHostileFixture(
            area="idp",
            scenario="mfa_challenge",
            target="Brookfield Entra ID",
            trigger="authorization response requires MFA interaction",
            expected_behavior="preserve the interaction_required result and send the clerk back through sign-in",
            fix="Complete the MFA challenge in the municipal identity provider, then return to CivicMeetings.",
            sample={"provider_family": "entra", "oauth_error": "interaction_required", "expected_status": 401},
        ),
        MockCityHostileFixture(
            area="idp",
            scenario="clock_skew_not_before",
            target="Brookfield Keycloak",
            trigger="token nbf is ahead of CivicMeetings' host clock",
            expected_behavior="reject with 401 and point the operator at clock synchronization",
            fix="Check clock synchronization between CivicMeetings and the IdP, then refresh the access token.",
            sample={"provider_family": "keycloak", "claim": "nbf", "expected_status": 401},
        ),
        MockCityHostileFixture(
            area="idp",
            scenario="refresh_required",
            target="Brookfield Okta",
            trigger="browser session is present but upstream access token requires refresh",
            expected_behavior="require a fresh OIDC sign-in without exposing any token material",
            fix="Open /staff/login, refresh the municipal IdP session, and retry the staff action.",
            sample={"provider_family": "okta", "oauth_error": "login_required", "expected_status": 401},
        ),
    ]


def mock_city_vendor_hostile_fixtures() -> list[MockCityHostileFixture]:
    """Return hostile agenda-vendor cases covering rate, paging, drift, and outage modes."""

    return [
        MockCityHostileFixture(
            area="vendor",
            scenario="rate_limit",
            target="legistar",
            trigger="HTTP 429 with Retry-After during a delta pull",
            expected_behavior="record a failed run, keep the cursor unchanged, and tell the operator when to retry",
            fix="Wait for the Retry-After window, confirm credentials are not shared across jobs, then retry.",
            sample={"http_status": 429, "retry_after_seconds": 120},
        ),
        MockCityHostileFixture(
            area="vendor",
            scenario="pagination",
            target="granicus",
            trigger="response contains a next page cursor after the first page of meetings",
            expected_behavior="continue from the next cursor before advancing the successful source cursor",
            fix="Follow the next page cursor until exhausted before marking the vendor pull successful.",
            sample={"page": 1, "next_cursor": "mock-page-2", "records": 50},
        ),
        MockCityHostileFixture(
            area="vendor",
            scenario="schema_drift",
            target="primegov",
            trigger="meeting title field is missing from a payload that used to be valid",
            expected_behavior="reject the payload with an actionable field-level import failure",
            fix="Update the PrimeGov adapter or vendor export mapping before enabling scheduled pulls.",
            sample={"meeting_id": "pg-drift-1", "scheduled_start": "2026-05-08T01:00:00Z", "items": []},
        ),
        MockCityHostileFixture(
            area="vendor",
            scenario="partial_outage",
            target="novusagenda",
            trigger="one payload in a multi-record response is malformed while another is usable",
            expected_behavior="record a partial run and keep the operator-facing failure tied to the bad record",
            fix="Fix the malformed record or connector mapping, then rerun before scheduled pulls resume.",
            sample={
                "payloads": [
                    {
                        "MeetingGuid": "nov-ok-1",
                        "MeetingTitle": "Parks Board",
                        "MeetingDateTime": "2026-05-09T17:00:00Z",
                        "Agenda": [{"Guid": "nov-item-1", "Caption": "Trail grant", "Dept": "Parks"}],
                    },
                    {"MeetingGuid": "nov-bad-1", "Agenda": []},
                ]
            },
        ),
        MockCityHostileFixture(
            area="vendor",
            scenario="duplicate_ids",
            target="legistar",
            trigger="two records in the same response share the same vendor meeting id",
            expected_behavior="quarantine duplicates instead of silently overwriting the first meeting",
            fix="Quarantine the duplicate IDs, ask the vendor which record is authoritative, then rerun.",
            sample={"duplicate_external_meeting_id": "leg-brookfield-100", "count": 2},
        ),
        MockCityHostileFixture(
            area="vendor",
            scenario="stale_delta",
            target="granicus",
            trigger="vendor returns records older than the persisted success cursor",
            expected_behavior="report a stale delta and keep the success cursor unchanged",
            fix="Verify the vendor delta parameter, reset the cursor only with clerk approval, then rerun.",
            sample={"cursor": "2026-05-10T12:00:00Z", "record_updated_at": "2026-05-01T12:00:00Z"},
        ),
    ]


def mock_city_backup_retention_hostile_fixtures() -> list[MockCityHostileFixture]:
    """Return hostile backup/off-host proof cases for retention conformance tests."""

    return [
        MockCityHostileFixture(
            area="backup_retention",
            scenario="delayed_restore",
            target=MOCK_CITY_NAME,
            trigger="monthly restore proof is older than the allowed interval",
            expected_behavior="fail readiness until a fresh restore rehearsal is attached",
            fix="Run a new restore rehearsal, attach the verification artifact, and update the evidence pack.",
            sample={"restore_proof_age_days": 45, "allowed_days": 30},
        ),
        MockCityHostileFixture(
            area="backup_retention",
            scenario="missing_manifest_fields",
            target=MOCK_CITY_NAME,
            trigger="backup manifest omits required dump checksum and restored table list",
            expected_behavior="fail readiness with the exact missing fields named",
            fix="Regenerate the backup manifest with dump.sha256 and restored_application_tables populated.",
            sample={"missing_fields": ["dump.sha256", "restored_application_tables"]},
        ),
        MockCityHostileFixture(
            area="backup_retention",
            scenario="stale_restore_proof",
            target=MOCK_CITY_NAME,
            trigger="restore proof predates the current application schema",
            expected_behavior="fail readiness until restore proof is rerun against the current schema",
            fix="Re-run restore after the latest migration, then attach the new restore-verification artifact.",
            sample={"proof_schema_revision": "civicclerk_0008", "current_schema_revision": "civicclerk_0010"},
        ),
        MockCityHostileFixture(
            area="backup_retention",
            scenario="legal_hold_conflict",
            target=MOCK_CITY_NAME,
            trigger="scheduled purge overlaps a legal hold on meeting records",
            expected_behavior="block purge and surface the legal-hold conflict to the operator",
            fix="Pause deletion for held records, document legal review, and rerun retention validation.",
            sample={"legal_hold": True, "scheduled_purge": True},
        ),
        MockCityHostileFixture(
            area="backup_retention",
            scenario="checksum_mismatch",
            target=MOCK_CITY_NAME,
            trigger="restored dump checksum differs from the backup manifest",
            expected_behavior="fail restore verification and prevent the backup from being accepted",
            fix="Reject the backup, preserve the failed evidence bundle, and create a new verified backup.",
            sample={"manifest_sha256": "mock-good", "restored_sha256": "mock-mismatch"},
        ),
    ]


def mock_city_hostile_fixtures() -> list[MockCityHostileFixture]:
    """Return every hostile-mode fixture exposed by the CivicMeetings mock-city suite."""

    return (
        mock_city_idp_hostile_fixtures()
        + mock_city_vendor_hostile_fixtures()
        + mock_city_backup_retention_hostile_fixtures()
    )


def run_mock_city_idp_contract_suite() -> list[MockCityIdpCheck]:
    """Validate CivicMeetings' mock municipal IdP contract without contacting an IdP."""

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


def run_mock_city_hostile_mode_suite() -> list[MockCityHostileCheck]:
    """Validate every hostile-mode fixture without contacting external systems."""

    checks: list[MockCityHostileCheck] = []
    for fixture in mock_city_hostile_fixtures():
        checks.append(_validate_hostile_fixture_shape(fixture))
        if fixture.area == "idp":
            checks.append(_validate_idp_hostile_fixture(fixture))
        elif fixture.area == "vendor":
            checks.append(_validate_vendor_hostile_fixture(fixture))
        elif fixture.area == "backup_retention":
            checks.append(_validate_backup_hostile_fixture(fixture))
    return checks


def _validate_hostile_fixture_shape(fixture: MockCityHostileFixture) -> MockCityHostileCheck:
    serialized = json.dumps(fixture.public_dict(), sort_keys=True).lower()
    leaked = [
        term
        for term in ("password", "client_secret_value", "token_value", "api_key_value")
        if term in serialized
    ]
    missing = [
        label
        for label, value in (
            ("trigger", fixture.trigger),
            ("expected_behavior", fixture.expected_behavior),
            ("fix", fixture.fix),
        )
        if not value.strip()
    ]
    fix_is_actionable = any(
        verb in fixture.fix.lower()
        for verb in (
            "ask",
            "attach",
            "check",
            "complete",
            "confirm",
            "pause",
            "follow",
            "map",
            "open",
            "preserve",
            "quarantine",
            "refresh",
            "regenerate",
            "reject",
            "rerun",
            "retry",
            "run",
            "set",
            "update",
            "verify",
            "wait",
        )
    )
    if leaked or missing or not fix_is_actionable:
        problems = []
        if leaked:
            problems.append("secret-like terms: " + ", ".join(leaked))
        if missing:
            problems.append("missing fields: " + ", ".join(missing))
        if not fix_is_actionable:
            problems.append("fix is not actionable")
        return MockCityHostileCheck(
            area=fixture.area,
            scenario=fixture.scenario,
            target=fixture.target,
            ok=False,
            message=f"Hostile fixture {fixture.scenario} is not publication-ready: {'; '.join(problems)}.",
            fix="Fill trigger, expected behavior, and imperative fix text without credential values.",
        )
    return MockCityHostileCheck(
        area=fixture.area,
        scenario=fixture.scenario,
        target=fixture.target,
        ok=True,
        message=f"Hostile fixture {fixture.scenario} is secret-free and has an actionable fix path.",
        fix="Keep this fixture in the hostile-mode suite whenever the mock contract changes.",
    )


def _validate_idp_hostile_fixture(fixture: MockCityHostileFixture) -> MockCityHostileCheck:
    contract = mock_city_idp_contract()
    config = _mock_city_oidc_config(contract)
    credentials: HTTPAuthorizationCredentials
    expected_status = int(fixture.sample.get("expected_status", 401))
    try:
        if fixture.scenario == "expired_access_token":
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=_mock_city_staff_token_with_claims(
                    contract,
                    expires_at=datetime.now(UTC) - timedelta(minutes=1),
                ),
            )
            authorize_oidc_staff_token(
                credentials,
                config=config,
                allowed_roles=MOCK_CITY_STAFF_ROLES,
                env_names=_mock_city_env_names(),
            )
        elif fixture.scenario == "group_claim_only":
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=_mock_city_staff_token_with_claims(
                    contract,
                    roles=(),
                    groups=("city_attorney",),
                ),
            )
            principal = authorize_oidc_staff_token(
                credentials,
                config=config,
                allowed_roles=MOCK_CITY_STAFF_ROLES,
                env_names=_mock_city_env_names(),
            )
            if expected_status == 200 and "city_attorney" in principal.roles:
                return MockCityHostileCheck(
                    area=fixture.area,
                    scenario=fixture.scenario,
                    target=fixture.target,
                    ok=True,
                    message="Group-claim-only OIDC token validated through the configured role-claim list.",
                    fix="Keep group-claim coverage when adding Okta or Keycloak tenants.",
                )
        elif fixture.scenario == "jwks_rotation":
            rotated_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=_mock_city_staff_token_with_claims(
                    contract,
                    signing_key=rotated_key,
                    key_id="brookfield-rotated-key",
                ),
            )
            authorize_oidc_staff_token(
                credentials,
                config=config,
                allowed_roles=MOCK_CITY_STAFF_ROLES,
                env_names=_mock_city_env_names(),
            )
        elif fixture.scenario == "clock_skew_not_before":
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=_mock_city_staff_token_with_claims(
                    contract,
                    not_before=datetime.now(UTC) + timedelta(minutes=10),
                ),
            )
            authorize_oidc_staff_token(
                credentials,
                config=config,
                allowed_roles=MOCK_CITY_STAFF_ROLES,
                env_names=_mock_city_env_names(),
            )
        else:
            if fixture.sample.get("oauth_error") and any(
                term in fixture.fix.lower() for term in ("complete", "login", "mfa", "refresh", "sign")
            ):
                return MockCityHostileCheck(
                    area=fixture.area,
                    scenario=fixture.scenario,
                    target=fixture.target,
                    ok=True,
                    message=f"{fixture.scenario} documents the browser OIDC refusal and recovery path.",
                    fix="Keep the OAuth error, user-facing message, and retry path together in this fixture.",
                )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        message = str(detail.get("message", ""))
        fix = str(detail.get("fix", ""))
        if exc.status_code == expected_status and message and fix:
            return MockCityHostileCheck(
                area=fixture.area,
                scenario=fixture.scenario,
                target=fixture.target,
                ok=True,
                message=f"{fixture.scenario} produced actionable OIDC refusal: {message}",
                fix=fix,
            )
        return MockCityHostileCheck(
            area=fixture.area,
            scenario=fixture.scenario,
            target=fixture.target,
            ok=False,
            message=f"{fixture.scenario} returned status {exc.status_code} without the expected actionable detail.",
            fix="Update OIDC hostile-mode validation so the refusal says what failed and how to recover.",
        )

    return MockCityHostileCheck(
        area=fixture.area,
        scenario=fixture.scenario,
        target=fixture.target,
        ok=False,
        message=f"{fixture.scenario} did not produce the expected hostile-mode outcome.",
        fix="Adjust the fixture or OIDC validation path so the hostile behavior is explicit.",
    )


def _validate_vendor_hostile_fixture(fixture: MockCityHostileFixture) -> MockCityHostileCheck:
    if fixture.scenario == "schema_drift":
        try:
            import_meeting_payload(connector_name=fixture.target, payload=fixture.sample)
        except ConnectorImportError as exc:
            public = exc.public_dict()
            if public.get("message") and public.get("fix"):
                return MockCityHostileCheck(
                    area=fixture.area,
                    scenario=fixture.scenario,
                    target=fixture.target,
                    ok=True,
                    message=public["message"],
                    fix=public["fix"],
                )
    elif fixture.scenario == "partial_outage":
        payloads = fixture.sample.get("payloads", [])
        successes = 0
        failures: list[str] = []
        for payload in payloads:
            try:
                import_meeting_payload(connector_name=fixture.target, payload=payload)
                successes += 1
            except ConnectorImportError as exc:
                failures.append(exc.public_dict()["message"])
        if successes and failures:
            return MockCityHostileCheck(
                area=fixture.area,
                scenario=fixture.scenario,
                target=fixture.target,
                ok=True,
                message=f"Partial outage fixture produced {successes} usable payload and {len(failures)} actionable failure.",
                fix=fixture.fix,
            )
    else:
        if fixture.target in {contract.connector for contract in mock_city_vendor_contracts()}:
            return MockCityHostileCheck(
                area=fixture.area,
                scenario=fixture.scenario,
                target=fixture.target,
                ok=True,
                message=f"{fixture.target} hostile fixture covers {fixture.trigger}.",
                fix=fixture.fix,
            )

    return MockCityHostileCheck(
        area=fixture.area,
        scenario=fixture.scenario,
        target=fixture.target,
        ok=False,
        message=f"{fixture.target} hostile fixture {fixture.scenario} did not validate.",
        fix="Update the vendor fixture so it maps to a supported connector and produces a concrete operator fix.",
    )


def _validate_backup_hostile_fixture(fixture: MockCityHostileFixture) -> MockCityHostileCheck:
    contract = mock_city_backup_retention_contract()
    expected_fields = set(contract.manifest_required_fields)
    sample_fields = set(fixture.sample.get("missing_fields", []))
    if fixture.scenario == "missing_manifest_fields" and not sample_fields.intersection(expected_fields):
        return MockCityHostileCheck(
            area=fixture.area,
            scenario=fixture.scenario,
            target=fixture.target,
            ok=False,
            message="Missing-manifest hostile fixture does not name a required manifest field.",
            fix="Name at least one field from the backup retention manifest contract.",
        )
    if fixture.target == contract.city and fixture.fix.strip():
        return MockCityHostileCheck(
            area=fixture.area,
            scenario=fixture.scenario,
            target=fixture.target,
            ok=True,
            message=f"Backup hostile fixture {fixture.scenario} maps to the Brookfield retention contract.",
            fix=fixture.fix,
        )
    return MockCityHostileCheck(
        area=fixture.area,
        scenario=fixture.scenario,
        target=fixture.target,
        ok=False,
        message=f"Backup hostile fixture {fixture.scenario} is not tied to the mock-city retention contract.",
        fix="Target the City of Brookfield backup-retention contract and include a recovery path.",
    )


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
    return _mock_city_staff_token_with_claims(
        contract,
        issued_at=now,
        expires_at=now + timedelta(minutes=15),
    )


def _mock_city_staff_token_with_claims(
    contract: MockCityIdpContract,
    *,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    not_before: datetime | None = None,
    roles: tuple[str, ...] | None = None,
    groups: tuple[str, ...] | None = None,
    signing_key: rsa.RSAPrivateKey | None = None,
    key_id: str = MOCK_CITY_IDP_KEY_ID,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "iss": contract.issuer,
        "aud": contract.audience,
        "sub": contract.staff_subject,
        "preferred_username": contract.staff_email,
        "iat": issued_at or now,
        "exp": expires_at or now + timedelta(minutes=15),
    }
    if roles is None:
        payload["roles"] = list(contract.staff_roles)
    elif roles:
        payload["roles"] = list(roles)
    if groups:
        payload["groups"] = list(groups)
    if not_before is not None:
        payload["nbf"] = not_before
    return jwt.encode(
        payload,
        signing_key or _mock_city_private_key(),
        algorithm="RS256",
        headers={"kid": key_id},
    )


@lru_cache(maxsize=1)
def _mock_city_private_key() -> rsa.RSAPrivateKey:
    """Generate one in-memory keypair per process for offline IdP contract validation."""

    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _mock_city_env_names() -> dict[str, str]:
    return {
        "issuer": "CIVICCLERK_STAFF_OIDC_ISSUER",
        "audience": "CIVICCLERK_STAFF_OIDC_AUDIENCE",
        "jwks_url": "CIVICCLERK_STAFF_OIDC_JWKS_URL",
        "jwks_json": "CIVICCLERK_STAFF_OIDC_JWKS_JSON",
        "role_claims": "CIVICCLERK_STAFF_OIDC_ROLE_CLAIMS",
        "algorithms": "CIVICCLERK_STAFF_OIDC_ALGORITHMS",
    }


__all__ = [
    "MOCK_CITY_CHANGED_SINCE",
    "MOCK_CITY_IDP_KEY_ID",
    "MOCK_CITY_INTERFACE_STATUS",
    "MOCK_CITY_NAME",
    "MOCK_CITY_STAFF_ROLES",
    "MockCityBackupRetentionCheck",
    "MockCityBackupRetentionContract",
    "MockCityContractCheck",
    "MockCityHostileCheck",
    "MockCityHostileFixture",
    "MockCityIdpCheck",
    "MockCityIdpContract",
    "MockCityVendorContract",
    "mock_city_backup_retention_contract",
    "mock_city_backup_retention_hostile_fixtures",
    "mock_city_hostile_fixtures",
    "mock_city_idp_contract",
    "mock_city_idp_hostile_fixtures",
    "mock_city_vendor_hostile_fixtures",
    "mock_city_vendor_contracts",
    "run_mock_city_backup_retention_suite",
    "run_mock_city_contract_suite",
    "run_mock_city_hostile_mode_suite",
    "run_mock_city_idp_contract_suite",
]
