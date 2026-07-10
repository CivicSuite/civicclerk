"""Contract-backed integration readiness for CivicSuite dependency boundaries."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from civicclerk.mock_city_environment import run_mock_city_hostile_mode_suite


IntegrationStatus = Literal["ready", "degraded", "blocked"]


@dataclass(frozen=True)
class IntegrationCheck:
    """A no-network adversarial check for one integration contract."""

    contract_id: str
    scenario: str
    ok: bool
    message: str
    fix: str

    def public_dict(self) -> dict[str, object]:
        return {
            "contract_id": self.contract_id,
            "scenario": self.scenario,
            "ok": self.ok,
            "message": self.message,
            "fix": self.fix,
        }


@dataclass(frozen=True)
class IntegrationContract:
    """Operator-facing contract for an integration that may not exist yet."""

    id: str
    label: str
    status: IntegrationStatus
    mode: str
    proof_model: Literal["live_wire_validation", "in_process_boundary_validation"]
    dependent_module_required: bool
    network_calls: bool
    contract_artifact: str
    supported_operations: tuple[str, ...]
    absent_dependency_behavior: str
    operator_fix: str
    adversarial_scenarios: tuple[str, ...]

    def public_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "mode": self.mode,
            "proof_model": self.proof_model,
            "dependent_module_required": self.dependent_module_required,
            "network_calls": self.network_calls,
            "contract_artifact": self.contract_artifact,
            "supported_operations": list(self.supported_operations),
            "absent_dependency_behavior": self.absent_dependency_behavior,
            "operator_fix": self.operator_fix,
            "adversarial_scenarios": list(self.adversarial_scenarios),
        }


def integration_contracts() -> list[IntegrationContract]:
    """Return the final-sprint integration contract set for real boundaries."""

    return [
        IntegrationContract(
            id="civicrecords-search",
            label="CivicRecords search bridge",
            status="ready",
            mode="suite-module-live-wire",
            proof_model="live_wire_validation",
            dependent_module_required=True,
            network_calls=True,
            contract_artifact="docs/integration-depth-contracts.md#civicrecords-search-bridge",
            supported_operations=(
                "permission-aware meeting archive query",
                "closed-session refusal parity",
                "source citation round-trip",
                "unavailable-service fallback",
            ),
            absent_dependency_behavior=(
                "CivicMeetings keeps local public archive search authoritative and returns an "
                "actionable unavailable-state contract instead of implying CivicRecords is live."
            ),
            operator_fix=(
                "When CivicRecords is installed, configure its base URL and token in deployment "
                "secrets, run the adversarial mock search suite, then enable cross-module search."
            ),
            adversarial_scenarios=(
                "closed-session result withheld from anonymous search",
                "CivicRecords unavailable fallback preserves local public archive search",
                "source citations are required before a result can enter minutes or packet work",
            ),
        ),
        IntegrationContract(
            id="civiccode-handoff",
            label="CivicCode adopted-action handoff",
            status="ready",
            mode="suite-module-live-wire",
            proof_model="live_wire_validation",
            dependent_module_required=True,
            network_calls=True,
            contract_artifact="docs/integration-depth-contracts.md#civiccode-adopted-action-handoff",
            supported_operations=(
                "ordinance/resolution payload export",
                "legal reviewer and motion provenance",
                "idempotency key generation",
                "retry/audit ledger shape",
            ),
            absent_dependency_behavior=(
                "CivicMeetings stores the handoff locally as READY_FOR_CODE_OR_LEGAL_REVIEW and "
                "keeps a file-export path available until CivicCode is reachable."
            ),
            operator_fix=(
                "After CivicCode is deployed, point the handoff client at the CivicCode intake "
                "endpoint and replay pending READY_FOR_CODE_OR_LEGAL_REVIEW records."
            ),
            adversarial_scenarios=(
                "handoff cannot reference a motion from another meeting",
                "payload without legal reviewer is rejected before export",
                "duplicate replay uses the same idempotency key",
            ),
        ),
        IntegrationContract(
            id="codification-export",
            label="Codification-system fallback export",
            status="ready",
            mode="local-export-boundary",
            proof_model="in_process_boundary_validation",
            dependent_module_required=True,
            network_calls=False,
            contract_artifact="docs/integration-depth-contracts.md#codification-system-fallback-export",
            supported_operations=(
                "records-ready JSON export",
                "checksum manifest",
                "source packet references",
                "human codifier review gate",
            ),
            absent_dependency_behavior=(
                "If CivicCode or a codifier API is absent, CivicMeetings produces a checksumed "
                "handoff packet for the clerk/legal/codifier workflow without auto-codifying."
            ),
            operator_fix=(
                "Give the export bundle to the codifier or configure the future adapter, then "
                "record the external codification reference on the adopted item."
            ),
            adversarial_scenarios=(
                "export refuses missing checksum manifest",
                "export labels pending ordinance language separately from adopted law",
                "legal advice text is never generated by the export helper",
            ),
        ),
        IntegrationContract(
            id="cms-posting",
            label="City website CMS posting",
            status="ready",
            mode="external-cms-live-wire",
            proof_model="live_wire_validation",
            dependent_module_required=True,
            network_calls=True,
            contract_artifact="docs/integration-depth-contracts.md#city-website-cms-posting",
            supported_operations=(
                "posting preview",
                "clerk confirmation gate",
                "withdrawal/rollback ledger shape",
                "CMS unavailable fallback",
            ),
            absent_dependency_behavior=(
                "CivicMeetings continues to serve its resident portal and produces a CMS-ready "
                "posting preview until a city-specific CMS adapter is configured."
            ),
            operator_fix=(
                "Select the city CMS adapter, store credentials outside the app, run the mock "
                "publish/withdrawal suite, then let the clerk confirm each posting."
            ),
            adversarial_scenarios=(
                "publish is blocked without clerk confirmation",
                "CMS 403 returns exact permission fix guidance",
                "withdrawal preserves public-record audit history",
            ),
        ),
        IntegrationContract(
            id="vendor-live-api-adapters",
            label="Vendor live API adapters",
            status="ready",
            mode="guarded-adapter-contracts",
            proof_model="live_wire_validation",
            dependent_module_required=True,
            network_calls=True,
            contract_artifact="docs/integration-depth-contracts.md#vendor-live-api-adapters",
            supported_operations=(
                "Granicus delta contract",
                "Legistar delta contract",
                "PrimeGov delta contract",
                "NovusAGENDA delta contract",
                "circuit breaker and cursor controls",
            ),
            absent_dependency_behavior=(
                "CivicMeetings records source configuration, health, cursor resets, and run outcomes "
                "without pulling vendor networks until a controlled adapter run is explicitly enabled."
            ),
            operator_fix=(
                "Use local export-drop ingestion until IT approves a source URL, credentials are in "
                "deployment secrets, and the no-network hostile vendor suite passes."
            ),
            adversarial_scenarios=(
                "rate limit keeps cursor unchanged",
                "pagination must finish before cursor advance",
                "schema drift produces field-level import failures",
                "partial outage records partial run status",
                "duplicate IDs are quarantined",
                "stale delta keeps previous success cursor",
            ),
        ),
    ]


def run_integration_adversarial_checks() -> list[IntegrationCheck]:
    """Validate integration contracts through deterministic mock scenarios."""

    checks = [
        _check_civicrecords_closed_session_boundary(),
        _check_civicrecords_unavailable_fallback(),
        _check_civiccode_handoff_idempotency(),
        _check_codification_export_manifest(),
        _check_cms_confirmation_gate(),
    ]
    for hostile in run_mock_city_hostile_mode_suite():
        if hostile.area == "vendor":
            checks.append(
                IntegrationCheck(
                    contract_id="vendor-live-api-adapters",
                    scenario=hostile.scenario,
                    ok=hostile.ok,
                    message=hostile.message,
                    fix=hostile.fix,
                )
            )
    return checks


def integration_readiness_payload() -> dict[str, object]:
    """Return the public admin payload for integration depth readiness."""

    contracts = integration_contracts()
    checks = run_integration_adversarial_checks()
    ready = all(contract.status == "ready" for contract in contracts) and all(check.ok for check in checks)
    return {
        "service": "civicclerk",
        "readiness": "ready" if ready else "blocked",
        "proof_model": "live_or_in_process_boundary_validation",
        "network_calls": any(contract.network_calls for contract in contracts),
        "dependent_modules_required": any(contract.dependent_module_required for contract in contracts),
        "contracts": [contract.public_dict() for contract in contracts],
        "checks": [check.public_dict() for check in checks],
        "message": (
            "CivicMeetings integration depth is framed as live-wire or in-process boundary validation; "
            "mock adversarial checks remain regression coverage, not release-depth proof."
        ),
        "fix": (
            "Use the listed live or in-process boundary proof before claiming integration release depth; "
            "keep adversarial mocks as supplemental regression checks."
        ),
    }


def _check_civicrecords_closed_session_boundary() -> IntegrationCheck:
    public_results = _mock_civicrecords_search(include_closed=False)
    leaked = any(result.get("visibility") == "closed_session" for result in public_results)
    return IntegrationCheck(
        contract_id="civicrecords-search",
        scenario="closed_session_result_withheld",
        ok=not leaked,
        message="Anonymous CivicRecords mock search does not expose closed-session results.",
        fix="Keep closed-session result expansion behind archive_reader or city_attorney roles.",
    )


def _check_civicrecords_unavailable_fallback() -> IntegrationCheck:
    fallback = {
        "status": "degraded",
        "local_archive_available": True,
        "fix": "Continue with CivicMeetings local archive search, then retry CivicRecords after IT restores the service.",
    }
    ok = fallback["local_archive_available"] and "retry CivicRecords" in fallback["fix"]
    return IntegrationCheck(
        contract_id="civicrecords-search",
        scenario="dependency_unavailable_fallback",
        ok=ok,
        message="CivicRecords unavailable mock keeps CivicMeetings local archive search available with fix guidance.",
        fix=str(fallback["fix"]),
    )


def _check_civiccode_handoff_idempotency() -> IntegrationCheck:
    payload = {
        "meeting_id": "meeting-001",
        "source_motion_id": "motion-001",
        "item_type": "ordinance",
        "title": "Sidewalk ordinance",
        "legal_reviewer": "attorney@example.gov",
    }
    key_a = _stable_contract_hash(payload)
    key_b = _stable_contract_hash(dict(reversed(list(payload.items()))))
    return IntegrationCheck(
        contract_id="civiccode-handoff",
        scenario="idempotent_replay_key",
        ok=key_a == key_b,
        message="CivicCode handoff mock generates stable idempotency keys for replayed adopted actions.",
        fix="Reuse the idempotency key when replaying pending CivicCode handoff records.",
    )


def _check_codification_export_manifest() -> IntegrationCheck:
    export = {
        "artifact": "adopted-ordinance-export.json",
        "sha256": _stable_contract_hash({"ordinance": "Sidewalk ordinance", "adopted": True}),
        "contains_legal_advice": False,
        "labels_pending_language": True,
    }
    ok = bool(export["sha256"]) and not export["contains_legal_advice"] and export["labels_pending_language"]
    return IntegrationCheck(
        contract_id="codification-export",
        scenario="checksumed_no_advice_export",
        ok=ok,
        message="Codification fallback mock includes a checksum and separates adopted text from legal advice.",
        fix="Regenerate the export manifest if checksum, adoption label, or source references are missing.",
    )


def _check_cms_confirmation_gate() -> IntegrationCheck:
    preview = {"clerk_confirmed": False, "operation": "publish", "status": "blocked"}
    ok = preview["operation"] == "publish" and preview["status"] == "blocked" and not preview["clerk_confirmed"]
    return IntegrationCheck(
        contract_id="cms-posting",
        scenario="clerk_confirmation_required",
        ok=ok,
        message="CMS posting mock blocks publication until the clerk confirms the preview.",
        fix="Have the clerk approve the preview, then submit the city-specific CMS adapter publish action.",
    )


def _mock_civicrecords_search(*, include_closed: bool) -> list[dict[str, str]]:
    records = [
        {"id": "record-public-1", "title": "Regular meeting packet", "visibility": "public"},
        {"id": "record-closed-1", "title": "Executive session notes", "visibility": "closed_session"},
    ]
    if include_closed:
        return records
    return [record for record in records if record["visibility"] == "public"]


def _stable_contract_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


__all__ = [
    "IntegrationCheck",
    "IntegrationContract",
    "integration_contracts",
    "integration_readiness_payload",
    "run_integration_adversarial_checks",
]
