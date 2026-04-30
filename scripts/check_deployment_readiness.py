"""Non-mutating CivicClerk deployment readiness preflight."""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException

from civicclerk import __version__
from civicclerk.main import (
    STAFF_AUTH_MODE_ENV_VAR,
    STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR,
    staff_auth_readiness,
)
from civiccore import __version__ as CIVICCORE_VERSION


ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT_ENV_VAR = "CIVICCLERK_DEPLOYMENT_PREFLIGHT_DIST_ROOT"
DATABASE_ENV_VARS = (
    "CIVICCLERK_AGENDA_INTAKE_DB_URL",
    "CIVICCLERK_AGENDA_ITEM_DB_URL",
    "CIVICCLERK_MEETING_DB_URL",
    "CIVICCLERK_PACKET_ASSEMBLY_DB_URL",
    "CIVICCLERK_NOTICE_CHECKLIST_DB_URL",
)
DOC_ARTIFACTS = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    ".gitignore",
    "docs/index.html",
)


@dataclass(frozen=True)
class Check:
    status: str
    name: str
    message: str
    fix: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a non-mutating CivicClerk deployment readiness report."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when the report is not deployment-ready.",
    )
    args = parser.parse_args()

    checks = build_checks()
    deployment_ready = all(check.status == "PASS" for check in checks)
    print_report(checks=checks, deployment_ready=deployment_ready)
    return 1 if args.strict and not deployment_ready else 0


def build_checks() -> list[Check]:
    checks: list[Check] = []
    checks.extend(_auth_checks())
    checks.extend(_database_checks())
    checks.extend(_export_root_checks())
    checks.extend(_release_artifact_checks())
    checks.extend(_documentation_checks())
    return checks


def print_report(*, checks: Iterable[Check], deployment_ready: bool) -> None:
    checks = list(checks)
    counts = {status: sum(1 for check in checks if check.status == status) for status in ("PASS", "WARN", "FAIL")}
    print("CivicClerk deployment readiness preflight")
    print(f"Version: civicclerk {__version__}; civiccore {CIVICCORE_VERSION}")
    print(f"deployment_ready={str(deployment_ready).lower()}")
    print(f"summary: pass={counts['PASS']} warn={counts['WARN']} fail={counts['FAIL']}")
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.message}")
        print(f"  fix: {check.fix}")


def _auth_checks() -> list[Check]:
    try:
        readiness = asyncio.run(staff_auth_readiness())
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        return [
            Check(
                status="FAIL",
                name="staff auth",
                message=detail.get("message", "Staff auth readiness could not be evaluated."),
                fix=detail.get("fix", f"Set {STAFF_AUTH_MODE_ENV_VAR} to open, bearer, or trusted_header."),
            )
        ]

    mode = str(readiness.get("mode", "unknown"))
    fix = str(readiness.get("fix", "Review /staff/auth-readiness before deployment."))
    if readiness.get("deployment_ready") is True:
        return [
            Check(
                status="PASS",
                name="staff auth",
                message=f"{mode} mode reports deployment_ready=true.",
                fix=fix,
            )
        ]
    if mode == "open":
        return [
            Check(
                status="WARN",
                name="staff auth",
                message="open mode is ready for local rehearsal but not real staff deployment.",
                fix=fix,
            )
        ]
    return [
        Check(
            status="FAIL",
            name="staff auth",
            message=f"{mode} mode is selected but not deployment-ready.",
            fix=fix,
        )
    ]


def _database_checks() -> list[Check]:
    missing = [name for name in DATABASE_ENV_VARS if not os.environ.get(name)]
    if not missing:
        return [
            Check(
                status="PASS",
                name="persistent stores",
                message="all deployment database URL environment variables are set; values are intentionally not printed.",
                fix="Run the staff write probes and migration checks against the configured databases before go-live.",
            )
        ]
    return [
        Check(
            status="WARN",
            name="persistent stores",
            message="missing deployment database URLs: " + ", ".join(missing),
            fix="Set the missing database URL environment variables before treating staff workflow data as durable.",
        )
    ]


def _export_root_checks() -> list[Check]:
    raw_export_root = os.environ.get("CIVICCLERK_EXPORT_ROOT", "exports")
    export_root = Path(raw_export_root)
    if not os.environ.get("CIVICCLERK_EXPORT_ROOT"):
        return [
            Check(
                status="WARN",
                name="packet export root",
                message="CIVICCLERK_EXPORT_ROOT is not set, so exports will use the local default ./exports.",
                fix="Set CIVICCLERK_EXPORT_ROOT to the deployment packet-export directory and ensure the service account can write there.",
            )
        ]
    if export_root.exists() and not export_root.is_dir():
        return [
            Check(
                status="FAIL",
                name="packet export root",
                message="CIVICCLERK_EXPORT_ROOT points to a file, not a directory.",
                fix="Set CIVICCLERK_EXPORT_ROOT to an existing directory or create the directory before packet export smoke checks.",
            )
        ]
    return [
        Check(
            status="PASS",
            name="packet export root",
            message="CIVICCLERK_EXPORT_ROOT is configured; path value is intentionally not printed.",
            fix="Run a packet export smoke check and confirm the generated manifest plus checksums land under that directory.",
        )
    ]


def _release_artifact_checks() -> list[Check]:
    dist_root = Path(os.environ.get(DIST_ROOT_ENV_VAR, ROOT / "dist"))
    required = (
        dist_root / f"civicclerk-{__version__}-py3-none-any.whl",
        dist_root / f"civicclerk-{__version__}.tar.gz",
        dist_root / "SHA256SUMS.txt",
    )
    missing = [_display_path(path) for path in required if not path.exists()]
    if not missing:
        return [
            Check(
                status="PASS",
                name="release artifacts",
                message="wheel, source distribution, and SHA256SUMS.txt are present.",
                fix="Use scripts/build_release_handoff_bundle.ps1 or scripts/build_release_handoff_bundle.sh to package the handoff bundle.",
            )
        ]
    return [
            Check(
                status="WARN",
                name="release artifacts",
                message="missing release artifacts: " + ", ".join(missing),
                fix=(
                    f"Run bash scripts/verify-release.sh before building or handing off release artifacts; "
                    f"set {DIST_ROOT_ENV_VAR} only when checking a non-default artifact directory."
                ),
            )
        ]


def _documentation_checks() -> list[Check]:
    missing_docs = [relative for relative in DOC_ARTIFACTS if not (ROOT / relative).exists()]
    checks: list[Check] = []
    if missing_docs:
        checks.append(
            Check(
                status="FAIL",
                name="documentation artifacts",
                message="missing required docs: " + ", ".join(missing_docs),
                fix="Create the missing docs before push, release, or deployment handoff.",
            )
        )
    else:
        checks.append(
            Check(
                status="PASS",
                name="documentation artifacts",
                message="all required documentation gate artifacts exist.",
                fix="Keep README, changelog, manual, docs landing page, and browser evidence in sync with deployment changes.",
            )
        )

    proxy_reference = ROOT / "docs" / "examples" / "trusted-header-nginx.conf"
    if proxy_reference.exists():
        checks.append(
            Check(
                status="PASS",
                name="trusted-header proxy reference",
                message="docs/examples/trusted-header-nginx.conf exists for reverse-proxy handoff.",
                fix=f"If trusted-header mode is used, set {STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR} and adapt the sample to the real proxy and TLS paths.",
            )
        )
    else:
        checks.append(
            Check(
                status="FAIL",
                name="trusted-header proxy reference",
                message="trusted-header nginx reference is missing.",
                fix="Restore docs/examples/trusted-header-nginx.conf before trusted-header deployment handoff.",
            )
        )
    return checks


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


if __name__ == "__main__":
    raise SystemExit(main())
