"""Summarize CivicClerk pilot readiness without pretending external proofs exist."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from civicclerk import __version__
from civicclerk.mock_city_environment import (
    MOCK_CITY_NAME,
    run_mock_city_contract_suite,
    run_mock_city_idp_contract_suite,
)
from scripts.check_installer_readiness import build_checks as build_installer_checks


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = __version__
DOC_WARNING_FILES = (
    "README.md",
    "README.txt",
    "USER-MANUAL.md",
    "USER-MANUAL.txt",
    "docs/index.html",
    "installer/windows/README.md",
)


@dataclass(frozen=True)
class Check:
    status: str
    name: str
    message: str
    fix: str
    owner: str

    def public_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "name": self.name,
            "message": self.message,
            "fix": self.fix,
            "owner": self.owner,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether CivicClerk is developer-ready for a municipal pilot handoff."
    )
    parser.add_argument("--version", default=DEFAULT_VERSION, help="CivicClerk version to verify.")
    parser.add_argument("--dist-root", default="dist", help="Directory containing release artifacts.")
    parser.add_argument(
        "--bundle",
        default="",
        help="Release handoff zip to verify. Defaults to dist/civicclerk-<version>-release-handoff.zip.",
    )
    parser.add_argument("--signing-proof", help="Optional code-signing certificate/procedure proof artifact.")
    parser.add_argument("--idp-proof", help="Optional municipal IdP configuration proof artifact.")
    parser.add_argument("--vendor-proof", help="Optional real municipal vendor API proof artifact.")
    parser.add_argument("--retention-proof", help="Optional city backup retention/off-host storage proof artifact.")
    parser.add_argument("--output", help="Optional JSON report path.")
    parser.add_argument(
        "--require-external-proof",
        action="store_true",
        help="Exit non-zero unless external proof artifacts are present too.",
    )
    parser.add_argument("--print-only", action="store_true", help="Print the readiness plan without checking files.")
    return parser.parse_args()


def build_checks(
    *,
    version: str,
    dist_root: Path,
    bundle_path: Path,
    signing_proof: str | None = None,
    idp_proof: str | None = None,
    vendor_proof: str | None = None,
    retention_proof: str | None = None,
) -> list[Check]:
    checks: list[Check] = []
    checks.extend(_installer_checks(version=version, dist_root=dist_root, bundle_path=bundle_path))
    checks.extend(_mock_city_checks())
    checks.extend(_unsigned_warning_checks())
    checks.extend(
        [
            _external_proof_check(
                name="code-signing certificate",
                proof_path=signing_proof,
                missing_message=(
                    "signed installer publication is certificate-gated; unsigned installer warnings are expected "
                    "during developer work."
                ),
                fix="Attach the enterprise signing proof once CivicSuite has an issued certificate and secured signing workstation.",
            ),
            _external_proof_check(
                name="municipal IdP deployment proof",
                proof_path=idp_proof,
                missing_message="OIDC is implemented, but a real city tenant/app registration has not been proven in this repo.",
                fix="Run the protected deployment smoke check against the city's IdP profile and attach the redacted result.",
            ),
            _external_proof_check(
                name="municipal vendor API proof",
                proof_path=vendor_proof,
                missing_message=(
                    "vendor-network sync is implemented behind explicit gates, but no real Granicus/Legistar/"
                    "PrimeGov/NovusAGENDA tenant proof is attached."
                ),
                fix="Run an approved one-source live sync from the municipal network and attach the secret-free report.",
            ),
            _external_proof_check(
                name="backup retention and off-host storage proof",
                proof_path=retention_proof,
                missing_message=(
                    "Docker/PostgreSQL restore rehearsal exists, but city retention schedule and off-host storage "
                    "approval are deployment-policy inputs."
                ),
                fix="Attach the city-approved retention/off-host backup runbook and latest restore rehearsal evidence.",
            ),
        ]
    )
    return checks


def _installer_checks(*, version: str, dist_root: Path, bundle_path: Path) -> list[Check]:
    checks = []
    for check in build_installer_checks(version=version, bundle_path=bundle_path, dist_root=dist_root):
        checks.append(
            Check(
                status=check.status,
                name=f"installer {check.name}",
                message=check.message,
                fix=check.fix,
                owner="developer",
            )
        )
    return checks


def _mock_city_checks() -> list[Check]:
    contract_checks = run_mock_city_contract_suite(base_url="https://mock-city.example.gov")
    idp_checks = run_mock_city_idp_contract_suite()
    checks: list[Check] = []
    if all(check.ok for check in contract_checks):
        checks.append(
            Check(
                status="PASS",
                name="mock city vendor contract suite",
                message=f"{MOCK_CITY_NAME} covers reusable no-network vendor contracts for future modules.",
                fix="Reuse this suite for module-specific integration assertions before adding real vendor tenants.",
                owner="developer",
            )
        )
    else:
        failed = [check.connector for check in contract_checks if not check.ok]
        checks.append(
            Check(
                status="FAIL",
                name="mock city vendor contract suite",
                message="mock city contracts failed for: " + ", ".join(failed),
                fix="Fix the reusable contract suite before using it as the baseline for other modules.",
                owner="developer",
            )
        )
    if all(check.ok for check in idp_checks):
        checks.append(
            Check(
                status="PASS",
                name="mock city municipal IdP contract suite",
                message=f"{MOCK_CITY_NAME} covers reusable no-network OIDC staff-auth contracts for future modules.",
                fix="Reuse this suite for module protected-auth assertions before attaching a real city tenant proof.",
                owner="developer",
            )
        )
    else:
        failed = [check.provider for check in idp_checks if not check.ok]
        checks.append(
            Check(
                status="FAIL",
                name="mock city municipal IdP contract suite",
                message="mock city IdP contracts failed for: " + ", ".join(failed),
                fix="Fix the reusable IdP contract suite before using it as the baseline for protected module tests.",
                owner="developer",
            )
        )
    return checks


def _unsigned_warning_checks() -> list[Check]:
    missing: list[str] = []
    for relative_path in DOC_WARNING_FILES:
        path = ROOT / relative_path
        if not path.exists():
            missing.append(relative_path)
            continue
        text = " ".join(path.read_text(encoding="utf-8").split())
        if "Unknown Publisher" not in text or "Windows protected your PC" not in text:
            missing.append(relative_path)
    if missing:
        return [
            Check(
                status="FAIL",
                name="unsigned installer warning docs",
                message="missing first-install Windows warning copy in: " + ", ".join(missing),
                fix="Add Unknown Publisher and Windows protected your PC guidance before handoff.",
                owner="developer",
            )
        ]
    return [
        Check(
            status="PASS",
            name="unsigned installer warning docs",
            message="all operator-facing docs warn about expected unsigned Windows installer prompts.",
            fix="Keep the warning until a real signing certificate and signed artifact exist.",
            owner="developer",
        )
    ]


def _external_proof_check(*, name: str, proof_path: str | None, missing_message: str, fix: str) -> Check:
    if proof_path and Path(proof_path).exists():
        return Check(
            status="PASS",
            name=name,
            message=f"proof artifact present: {_display(Path(proof_path))}.",
            fix="Keep the proof artifact with the pilot handoff packet.",
            owner="external",
        )
    return Check(
        status="EXTERNAL",
        name=name,
        message=missing_message,
        fix=fix,
        owner="external",
    )


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _payload(checks: list[Check]) -> dict[str, object]:
    developer_ready = all(check.status == "PASS" for check in checks if check.owner == "developer")
    external_pending = any(check.status == "EXTERNAL" for check in checks)
    return {
        "product": "CivicClerk",
        "version": __version__,
        "developer_ready": developer_ready,
        "external_dependencies_pending": external_pending,
        "network_calls": False,
        "checks": [check.public_dict() for check in checks],
    }


def _print_report(checks: list[Check]) -> None:
    payload = _payload(checks)
    print("CivicClerk pilot readiness")
    print(f"Version: {__version__}")
    print("network_calls=false")
    print(f"developer_ready={str(payload['developer_ready']).lower()}")
    print(f"external_dependencies_pending={str(payload['external_dependencies_pending']).lower()}")
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.message}")
        print(f"  owner: {check.owner}")
        print(f"  fix: {check.fix}")
    if payload["developer_ready"]:
        print("PILOT-READINESS: DEVELOPER-READY")
    else:
        print("PILOT-READINESS: FAILED")


def _print_plan(version: str, dist_root: Path, bundle_path: Path) -> None:
    print("CivicClerk pilot readiness")
    print(f"Version: {version}")
    print("Network calls: none")
    print(f"Dist root: {_display(dist_root)}")
    print(f"Handoff bundle: {_display(bundle_path)}")
    print("Developer-owned checks:")
    print("  1. Release artifacts and handoff bundle are present and checksum-valid.")
    print("  2. Mock city vendor contracts pass without contacting vendor networks.")
    print("  3. Mock city municipal IdP contracts pass without contacting an IdP.")
    print("  4. Operator docs warn about unsigned Windows first-install prompts.")
    print("External proof slots:")
    print("  - code-signing certificate and signed-artifact proof")
    print("  - municipal IdP protected-deployment proof")
    print("  - municipal vendor API live-sync proof")
    print("  - city backup retention/off-host storage proof")
    print("PILOT-READINESS: PLAN")


def main() -> int:
    args = parse_args()
    dist_root = Path(args.dist_root)
    bundle_path = Path(args.bundle) if args.bundle else dist_root / f"civicclerk-{args.version}-release-handoff.zip"
    if args.print_only:
        _print_plan(args.version, dist_root, bundle_path)
        return 0

    checks = build_checks(
        version=args.version,
        dist_root=dist_root,
        bundle_path=bundle_path,
        signing_proof=args.signing_proof,
        idp_proof=args.idp_proof,
        vendor_proof=args.vendor_proof,
        retention_proof=args.retention_proof,
    )
    payload = _payload(checks)
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _print_report(checks)
    if not payload["developer_ready"]:
        return 1
    if args.require_external_proof and payload["external_dependencies_pending"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
