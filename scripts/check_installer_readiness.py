"""Verify CivicClerk release handoff inputs are ready for installer packaging."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "0.1.14"


def _bundle_entries(version: str) -> tuple[str, ...]:
    return (
        "README.md",
        "README.txt",
        "USER-MANUAL.md",
        "USER-MANUAL.txt",
        "CHANGELOG.md",
        "LICENSE",
        "docs/index.html",
        "docs/examples/deployment.env.example",
        "docs/examples/trusted-header-nginx.conf",
        "scripts/check_installer_readiness.py",
        "scripts/check_pilot_readiness.py",
        "scripts/check_enterprise_installer_signing.py",
        "scripts/check_connector_sync_readiness.py",
        "scripts/check_vendor_live_sync_readiness.py",
        "scripts/run_mock_city_environment_suite.py",
        "scripts/run_connector_import_sync.py",
        "scripts/run_vendor_live_sync.py",
        "scripts/start_fresh_install_rehearsal.ps1",
        "scripts/start_fresh_install_rehearsal.sh",
        "scripts/check_backup_restore_rehearsal.py",
        "scripts/check_protected_deployment_smoke.py",
        "scripts/start_backup_restore_rehearsal.ps1",
        "scripts/start_backup_restore_rehearsal.sh",
        "scripts/start_protected_demo_rehearsal.ps1",
        "scripts/start_protected_demo_rehearsal.sh",
        "scripts/local_trusted_header_proxy.py",
        f"dist/civicclerk-{version}-py3-none-any.whl",
        f"dist/civicclerk-{version}.tar.gz",
        "dist/SHA256SUMS.txt",
    )


@dataclass(frozen=True)
class Check:
    status: str
    name: str
    message: str
    fix: str


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _read_checksum_file(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, filename = line.partition("  ")
        if not digest or not filename:
            raise ValueError("expected '<sha256>  <filename>' lines")
        checksums[filename.strip()] = digest.strip()
    return checksums


def _checksum_checks(dist_root: Path, version: str) -> list[Check]:
    wheel = dist_root / f"civicclerk-{version}-py3-none-any.whl"
    sdist = dist_root / f"civicclerk-{version}.tar.gz"
    checksum_file = dist_root / "SHA256SUMS.txt"
    missing = [path for path in (wheel, sdist, checksum_file) if not path.exists()]
    if missing:
        return [
            Check(
                status="FAIL",
                name="release artifacts",
                message="missing installer input artifacts: " + ", ".join(_display(path) for path in missing),
                fix="Run bash scripts/verify-release.sh before installer readiness or handoff packaging.",
            )
        ]

    try:
        expected = _read_checksum_file(checksum_file)
    except ValueError as exc:
        return [
            Check(
                status="FAIL",
                name="checksums",
                message=f"{_display(checksum_file)} is malformed: {exc}.",
                fix="Regenerate release artifacts with bash scripts/verify-release.sh.",
            )
        ]

    failures: list[str] = []
    for artifact in (wheel, sdist):
        expected_digest = expected.get(artifact.name)
        actual_digest = sha256(artifact.read_bytes()).hexdigest()
        if expected_digest != actual_digest:
            failures.append(artifact.name)
    if failures:
        return [
            Check(
                status="FAIL",
                name="checksums",
                message="checksum mismatch for: " + ", ".join(failures),
                fix="Regenerate dist artifacts and SHA256SUMS.txt with bash scripts/verify-release.sh.",
            )
        ]
    return [
        Check(
            status="PASS",
            name="checksums",
            message="wheel and source distribution match dist/SHA256SUMS.txt.",
            fix="Keep SHA256SUMS.txt bundled with the installer inputs.",
        )
    ]


def build_checks(*, version: str, bundle_path: Path, dist_root: Path) -> list[Check]:
    checks = _checksum_checks(dist_root, version)
    expected_entries = set(_bundle_entries(version))
    if not bundle_path.exists():
        checks.append(
            Check(
                status="FAIL",
                name="handoff bundle",
                message=f"release handoff bundle is missing: {_display(bundle_path)}.",
                fix="Run scripts/build_release_handoff_bundle.ps1 or scripts/build_release_handoff_bundle.sh after verify-release.sh.",
            )
        )
        return checks
    if not zipfile.is_zipfile(bundle_path):
        checks.append(
            Check(
                status="FAIL",
                name="handoff bundle",
                message=f"release handoff bundle is not a valid zip: {_display(bundle_path)}.",
                fix="Delete the invalid file and rebuild the handoff bundle from verified release artifacts.",
            )
        )
        return checks

    with zipfile.ZipFile(bundle_path) as bundle:
        actual_entries = set(bundle.namelist())
    missing_entries = sorted(expected_entries - actual_entries)
    if missing_entries:
        checks.append(
            Check(
                status="FAIL",
                name="handoff bundle entries",
                message="missing installer input entries: " + ", ".join(missing_entries),
                fix="Rebuild the handoff bundle with scripts/build_release_handoff_bundle.ps1 or scripts/build_release_handoff_bundle.sh.",
            )
        )
    else:
        checks.append(
            Check(
                status="PASS",
                name="handoff bundle entries",
                message="release handoff bundle contains every required installer input.",
                fix="Use this zip as the source contract for the future Windows installer package.",
            )
        )
    return checks


def _print_report(checks: list[Check]) -> int:
    ready = all(check.status == "PASS" for check in checks)
    print("CivicClerk installer readiness")
    print(f"installer_ready={str(ready).lower()}")
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.message}")
        print(f"  fix: {check.fix}")
    print("INSTALLER-READINESS: PASSED" if ready else "INSTALLER-READINESS: FAILED")
    return 0 if ready else 1


def _print_plan(version: str, bundle_path: Path, dist_root: Path) -> None:
    print("CivicClerk installer readiness")
    print(f"Version: {version}")
    print(f"Dist root: {_display(dist_root)}")
    print(f"Handoff bundle: {_display(bundle_path)}")
    print("Steps:")
    print("  1. Confirm verify-release.sh produced the wheel, source distribution, and SHA256SUMS.txt.")
    print("  2. Confirm SHA256SUMS.txt matches the wheel and source distribution.")
    print("  3. Confirm the release handoff zip exists and is a valid zip.")
    print("  4. Confirm the zip contains docs, release artifacts, env examples, and rehearsal helpers.")
    print("Fix path: run bash scripts/verify-release.sh, then build the handoff bundle, then rerun this check.")
    print("Not an installer: this verifies installer inputs before a future MSI or setup package exists.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify CivicClerk installer packaging inputs.")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="CivicClerk version to verify.")
    parser.add_argument("--dist-root", default="dist", help="Directory containing release artifacts.")
    parser.add_argument(
        "--bundle",
        default="",
        help="Release handoff zip to verify. Defaults to dist/civicclerk-<version>-release-handoff.zip.",
    )
    parser.add_argument("--print-only", action="store_true", help="Print the installer readiness plan without checking files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dist_root = Path(args.dist_root)
    bundle_path = Path(args.bundle) if args.bundle else dist_root / f"civicclerk-{args.version}-release-handoff.zip"
    if args.print_only:
        _print_plan(args.version, bundle_path, dist_root)
        return 0
    return _print_report(build_checks(version=args.version, bundle_path=bundle_path, dist_root=dist_root))


if __name__ == "__main__":
    raise SystemExit(main())
