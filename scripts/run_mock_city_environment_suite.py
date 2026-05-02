"""Run the reusable CivicSuite mock-city environment contract suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from civicclerk.mock_city_environment import (
    MOCK_CITY_NAME,
    mock_city_idp_contract,
    mock_city_vendor_contracts,
    run_mock_city_contract_suite,
    run_mock_city_idp_contract_suite,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate reusable mock-city vendor contracts without contacting vendor networks."
    )
    parser.add_argument(
        "--base-url",
        default="https://mock-city.example.gov",
        help="Base URL used only to render planned request URLs. No network calls are made.",
    )
    parser.add_argument("--output", help="Optional JSON report path.")
    parser.add_argument("--print-only", action="store_true", help="Print the reusable mock-city plan without checks.")
    return parser.parse_args()


def _write_report(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_plan(base_url: str) -> int:
    print("CivicSuite mock city environment suite")
    print(f"mock_city={MOCK_CITY_NAME}")
    print("network_calls=false")
    print(f"base_url={base_url}")
    print("Reusable vendor interface contracts:")
    for contract in mock_city_vendor_contracts():
        print(
            f"- {contract.connector}: {contract.method} {contract.path} "
            f"auth={contract.auth_method} status={contract.interface_status} "
            f"delta={contract.delta_query_param}"
        )
    idp = mock_city_idp_contract()
    print("Reusable municipal IdP contract:")
    print(
        f"- {idp.provider}: issuer={idp.issuer} audience={idp.audience} "
        f"auth_code_pkce=true jwks={idp.jwks_path} roles={','.join(idp.role_claims)} "
        "secrets_reported=false"
    )
    print("Fix path: module teams should reuse these contracts and add only module-specific assertions.")
    print("MOCK-CITY-ENVIRONMENT-SUITE: PLAN")
    return 0


def main() -> int:
    args = parse_args()
    if args.print_only:
        return _print_plan(args.base_url)

    checks = run_mock_city_contract_suite(base_url=args.base_url)
    idp_checks = run_mock_city_idp_contract_suite()
    ready = all(check.ok for check in checks) and all(check.ok for check in idp_checks)
    payload = {
        "mock_city": MOCK_CITY_NAME,
        "network_calls": False,
        "base_url": args.base_url,
        "contracts": [contract.public_dict() for contract in mock_city_vendor_contracts()],
        "idp_contract": mock_city_idp_contract().public_dict(),
        "checks": [check.public_dict() for check in checks],
        "idp_checks": [check.public_dict() for check in idp_checks],
        "ready": ready,
    }
    if args.output:
        _write_report(args.output, payload)

    print("CivicSuite mock city environment suite")
    print(f"mock_city={MOCK_CITY_NAME}")
    print(f"ready={str(ready).lower()}")
    print("network_calls=false")
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"[{status}] {check.connector}: {check.message}")
        print(f"  fix: {check.fix}")
        if check.delta_request_url:
            print(f"  planned_delta_url: {check.delta_request_url}")
    for check in idp_checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"[{status}] municipal-idp: {check.message}")
        print(f"  fix: {check.fix}")
        if check.roles:
            print(f"  roles: {', '.join(check.roles)}")
    print("MOCK-CITY-ENVIRONMENT-SUITE: PASSED" if ready else "MOCK-CITY-ENVIRONMENT-SUITE: FAILED")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
