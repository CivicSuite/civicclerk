from __future__ import annotations

"""Live-boundary contract tests for CivicMeetings integration depth declarations."""

from civicclerk.integration_contracts import integration_contracts, integration_readiness_payload


def test_declared_integration_contracts_require_live_or_in_process_proof() -> None:
    contracts = {contract.id: contract for contract in integration_contracts()}

    assert set(contracts) == {
        "civicrecords-search",
        "civiccode-handoff",
        "codification-export",
        "cms-posting",
        "vendor-live-api-adapters",
    }
    for contract in contracts.values():
        assert contract.network_calls is True or contract.dependent_module_required is True
        assert contract.proof_model in {"live_wire_validation", "in_process_boundary_validation"}


def test_readiness_payload_no_longer_claims_mock_validation_as_release_depth() -> None:
    payload = integration_readiness_payload()

    assert payload["proof_model"] == "live_or_in_process_boundary_validation"
    assert payload["network_calls"] is True
    assert payload["dependent_modules_required"] is True
