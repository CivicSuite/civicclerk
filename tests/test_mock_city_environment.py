from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from civicclerk.mock_city_environment import (
    MOCK_CITY_NAME,
    mock_city_backup_retention_hostile_fixtures,
    mock_city_hostile_fixtures,
    mock_city_backup_retention_contract,
    mock_city_idp_contract,
    mock_city_idp_hostile_fixtures,
    mock_city_vendor_hostile_fixtures,
    mock_city_vendor_contracts,
    run_mock_city_backup_retention_suite,
    run_mock_city_contract_suite,
    run_mock_city_hostile_mode_suite,
    run_mock_city_idp_contract_suite,
)


ROOT = Path(__file__).resolve().parents[1]


def test_mock_city_contracts_cover_supported_agenda_vendor_interfaces() -> None:
    contracts = {contract.connector: contract for contract in mock_city_vendor_contracts()}

    assert set(contracts) == {"granicus", "legistar", "novusagenda", "primegov"}
    assert MOCK_CITY_NAME == "City of Brookfield"
    assert contracts["legistar"].interface_status == "public-reference"
    assert contracts["legistar"].path == "/v1/{Client}/Events?EventItems=true"
    assert contracts["legistar"].delta_query_param == "LastModifiedDate"
    assert contracts["granicus"].interface_status == "vendor-gated-contract"
    assert contracts["primegov"].delta_query_param == "updated_since"
    assert contracts["novusagenda"].delta_query_param == "modifiedSince"


def test_mock_city_suite_normalizes_payloads_and_plans_delta_urls() -> None:
    checks = run_mock_city_contract_suite(base_url="https://mock-city.example.gov")

    assert len(checks) == 4
    assert all(check.ok for check in checks)
    by_connector = {check.connector: check for check in checks}
    assert by_connector["legistar"].normalized_external_meeting_id == "leg-brookfield-100"
    assert "LastModifiedDate=2026-05-01T12%3A00%3A00Z" in by_connector["legistar"].delta_request_url
    assert "modifiedSince=2026-05-01T12%3A00%3A00Z" in by_connector["granicus"].delta_request_url
    assert "updated_since=2026-05-01T12%3A00%3A00Z" in by_connector["primegov"].delta_request_url
    assert "network" not in " ".join(check.message.lower() for check in checks)


def test_mock_city_idp_contract_validates_staff_oidc_without_network() -> None:
    contract = mock_city_idp_contract()
    checks = run_mock_city_idp_contract_suite()

    assert contract.provider == "Brookfield Entra ID"
    assert contract.interface_status == "mock-municipal-idp"
    assert contract.jwks_path.endswith("/keys")
    assert contract.role_claims == ("roles", "groups")
    assert contract.algorithms == ("RS256",)
    assert len(checks) == 1
    assert checks[0].ok is True
    assert checks[0].auth_method == "oidc"
    assert checks[0].subject == "clerk@brookfield.example.gov"
    assert checks[0].roles == ("clerk_admin", "meeting_editor")


def test_mock_city_backup_retention_contract_validates_off_host_policy_without_network() -> None:
    contract = mock_city_backup_retention_contract()
    checks = run_mock_city_backup_retention_suite()

    assert contract.city == MOCK_CITY_NAME
    assert contract.interface_status == "mock-policy-contract"
    assert contract.retention_years >= 7
    assert contract.restore_test_interval_days <= 30
    assert contract.off_host_storage.startswith("mock://")
    assert contract.restore_proof_required is True
    assert contract.encryption_at_rest_required is True
    assert contract.immutable_retention_required is True
    assert contract.legal_hold_supported is True
    assert "dump.sha256" in contract.manifest_required_fields
    assert len(checks) == 1
    assert checks[0].ok is True
    assert "seven-year retention" in checks[0].message


def test_mock_city_contracts_are_public_and_secret_free() -> None:
    serialized = json.dumps(
        {
            "vendor_contracts": [contract.public_dict() for contract in mock_city_vendor_contracts()],
            "idp_contract": mock_city_idp_contract().public_dict(),
            "idp_checks": [check.public_dict() for check in run_mock_city_idp_contract_suite()],
            "backup_retention_contract": mock_city_backup_retention_contract().public_dict(),
            "backup_retention_checks": [
                check.public_dict() for check in run_mock_city_backup_retention_suite()
            ],
        }
    ).lower()

    assert "password" not in serialized
    assert "secret" not in serialized
    assert "token_value" not in serialized
    assert "api_key_value" not in serialized
    assert "tenant-specific" in serialized


def test_mock_city_hostile_fixtures_cover_cc2_required_failure_modes() -> None:
    fixtures = mock_city_hostile_fixtures()
    scenarios = {fixture.scenario for fixture in fixtures}
    vendor_targets = {fixture.target for fixture in mock_city_vendor_hostile_fixtures()}
    idp_targets = {fixture.target for fixture in mock_city_idp_hostile_fixtures()}
    backup_scenarios = {fixture.scenario for fixture in mock_city_backup_retention_hostile_fixtures()}

    assert {
        "expired_access_token",
        "group_claim_only",
        "jwks_rotation",
        "mfa_challenge",
        "clock_skew_not_before",
        "refresh_required",
        "rate_limit",
        "pagination",
        "schema_drift",
        "partial_outage",
        "duplicate_ids",
        "stale_delta",
        "delayed_restore",
        "missing_manifest_fields",
        "stale_restore_proof",
        "legal_hold_conflict",
        "checksum_mismatch",
    } <= scenarios
    assert {"legistar", "granicus", "primegov", "novusagenda"} <= vendor_targets
    assert {"Brookfield Entra ID", "Brookfield Okta", "Brookfield Keycloak"} <= idp_targets
    assert {
        "delayed_restore",
        "missing_manifest_fields",
        "stale_restore_proof",
        "legal_hold_conflict",
        "checksum_mismatch",
    } == backup_scenarios

    serialized = json.dumps([fixture.public_dict() for fixture in fixtures]).lower()
    assert "password" not in serialized
    assert "client_secret_value" not in serialized
    assert "token_value" not in serialized
    assert "api_key_value" not in serialized


def test_mock_city_hostile_mode_suite_validates_actionable_failures_without_network() -> None:
    checks = run_mock_city_hostile_mode_suite()

    assert checks
    assert all(check.ok for check in checks)
    by_scenario = {check.scenario: check for check in checks if check.area == "idp"}
    assert "OIDC token has expired" in by_scenario["expired_access_token"].message
    assert "Group-claim-only" in by_scenario["group_claim_only"].message
    assert "OIDC token is not valid yet" in by_scenario["clock_skew_not_before"].message
    assert "clock synchronization" in by_scenario["clock_skew_not_before"].fix
    assert any(
        check.scenario == "schema_drift"
        and "PrimeGov meeting payload is missing required field title" in check.message
        for check in checks
    )
    assert any(check.scenario == "partial_outage" and "Partial outage" in check.message for check in checks)
    assert any(check.scenario == "checksum_mismatch" and "Reject the backup" in check.fix for check in checks)


def test_mock_city_environment_cli_writes_reusable_report(tmp_path: Path) -> None:
    output = tmp_path / "mock-city-report.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_mock_city_environment_suite.py",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "network_calls=false" in result.stdout
    assert "MOCK-CITY-ENVIRONMENT-SUITE: PASSED" in result.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["mock_city"] == "City of Brookfield"
    assert report["network_calls"] is False
    assert report["hostile_mode"] is False
    assert report["ready"] is True
    assert {contract["connector"] for contract in report["contracts"]} == {
        "granicus",
        "legistar",
        "novusagenda",
        "primegov",
    }
    assert report["idp_contract"]["provider"] == "Brookfield Entra ID"
    assert report["idp_contract"]["redirect_uri"].endswith("/staff/oidc/callback")
    assert report["idp_checks"][0]["ok"] is True
    assert report["idp_checks"][0]["roles"] == ["clerk_admin", "meeting_editor"]
    assert report["backup_retention_contract"]["retention_years"] == 7
    assert report["backup_retention_contract"]["off_host_storage"].startswith("mock://")
    assert report["backup_retention_checks"][0]["ok"] is True
    assert "dump.sha256" in report["backup_retention_checks"][0]["checked_fields"]
    serialized = json.dumps(report).lower()
    assert "mock-client-secret" not in serialized
    assert "mock-session-secret" not in serialized


def test_mock_city_environment_cli_writes_hostile_mode_report(tmp_path: Path) -> None:
    output = tmp_path / "mock-city-hostile-report.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_mock_city_environment_suite.py",
            "--hostile-mode",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "hostile_mode=true" in result.stdout
    assert "[PASS] hostile/idp/expired_access_token" in result.stdout
    assert "[PASS] hostile/vendor/rate_limit" in result.stdout
    assert "[PASS] hostile/backup_retention/checksum_mismatch" in result.stdout
    assert "MOCK-CITY-ENVIRONMENT-SUITE: PASSED" in result.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["hostile_mode"] is True
    assert report["ready"] is True
    assert {fixture["area"] for fixture in report["hostile_fixtures"]} == {
        "idp",
        "vendor",
        "backup_retention",
    }
    assert all(check["ok"] for check in report["hostile_checks"])
    serialized = json.dumps(report).lower()
    assert "password" not in serialized
    assert "client_secret_value" not in serialized
    assert "token_value" not in serialized
    assert "api_key_value" not in serialized


def test_mock_city_environment_cli_prints_hostile_plan() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_mock_city_environment_suite.py",
            "--hostile-mode",
            "--print-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "hostile_mode=true" in result.stdout
    assert "Hostile-mode fixtures:" in result.stdout
    assert "idp/clock_skew_not_before" in result.stdout
    assert "vendor/stale_delta" in result.stdout
    assert "backup_retention/legal_hold_conflict" in result.stdout


def test_mock_city_hostile_mode_docs_are_current() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.txt").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
            (ROOT / "scripts/verify-docs.sh").read_text(encoding="utf-8"),
        ]
    )

    for expected in (
        "--hostile-mode",
        "mock-city-hostile-report.json",
        "JWKS rotation",
        "clock skew",
        "schema drift",
        "partial outage",
        "legal-hold",
        "checksum",
    ):
        assert expected in docs
