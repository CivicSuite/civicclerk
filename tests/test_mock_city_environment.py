from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from civicclerk.mock_city_environment import (
    MOCK_CITY_NAME,
    mock_city_idp_contract,
    mock_city_vendor_contracts,
    run_mock_city_contract_suite,
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


def test_mock_city_contracts_are_public_and_secret_free() -> None:
    serialized = json.dumps(
        {
            "vendor_contracts": [contract.public_dict() for contract in mock_city_vendor_contracts()],
            "idp_contract": mock_city_idp_contract().public_dict(),
            "idp_checks": [check.public_dict() for check in run_mock_city_idp_contract_suite()],
        }
    ).lower()

    assert "password" not in serialized
    assert "secret" not in serialized
    assert "token_value" not in serialized
    assert "api_key_value" not in serialized
    assert "tenant-specific" in serialized


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
    serialized = json.dumps(report).lower()
    assert "mock-client-secret" not in serialized
    assert "mock-session-secret" not in serialized
