"""Reusable mock city integration contracts for CivicSuite modules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from civicclerk.connectors import SUPPORTED_CONNECTORS, import_meeting_payload
from civicclerk.vendor_delta import plan_vendor_delta_request


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
