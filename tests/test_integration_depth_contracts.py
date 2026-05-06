from __future__ import annotations

from fastapi.testclient import TestClient

from civicclerk.integration_contracts import (
    integration_contracts,
    integration_readiness_payload,
    run_integration_adversarial_checks,
)
from civicclerk.main import app


def test_integration_contracts_cover_unfinished_unified_spec_depth_without_dependencies() -> None:
    contracts = {contract.id: contract for contract in integration_contracts()}

    assert set(contracts) == {
        "civicrecords-search",
        "civiccode-handoff",
        "codification-export",
        "cms-posting",
        "vendor-live-api-adapters",
    }
    for contract in contracts.values():
        assert contract.status == "ready"
        assert contract.network_calls is False
        assert contract.dependent_module_required is False
        assert contract.absent_dependency_behavior
        assert contract.operator_fix
        assert contract.supported_operations
        assert contract.adversarial_scenarios


def test_integration_adversarial_checks_are_actionable_and_no_network() -> None:
    checks = run_integration_adversarial_checks()

    assert checks
    assert all(check.ok for check in checks)
    assert {check.contract_id for check in checks}.issuperset(
        {
            "civicrecords-search",
            "civiccode-handoff",
            "codification-export",
            "cms-posting",
            "vendor-live-api-adapters",
        }
    )
    for check in checks:
        assert check.message
        assert check.fix


def test_integration_readiness_payload_is_release_proof_ready() -> None:
    payload = integration_readiness_payload()

    assert payload["readiness"] == "ready"
    assert payload["proof_model"] == "adversarial_mock_validation"
    assert payload["network_calls"] is False
    assert payload["dependent_modules_required"] is False
    assert len(payload["contracts"]) == 5
    assert len(payload["checks"]) >= 10


def test_integration_readiness_endpoint_is_published_and_actionable() -> None:
    response = TestClient(app).get("/integrations/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["readiness"] == "ready"
    assert payload["network_calls"] is False
    assert "CivicRecords" in payload["message"]
    assert "adversarial mocks" in payload["fix"]
