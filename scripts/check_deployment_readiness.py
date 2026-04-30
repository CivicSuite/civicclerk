"""Non-mutating CivicClerk deployment readiness preflight."""

from __future__ import annotations

import argparse
import asyncio
import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException

from civicclerk import __version__
from civicclerk.main import (
    STAFF_AUTH_MODE_ENV_VAR,
    STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR,
    STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
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
    parser.add_argument(
        "--env-file",
        help=(
            "Load KEY=VALUE lines from a deployment profile before checking. "
            "Comments and blank lines are ignored; existing process env values win."
        ),
    )
    args = parser.parse_args()

    loaded_env_file = _load_env_file(Path(args.env_file)) if args.env_file else None
    checks = build_checks()
    deployment_ready = all(check.status == "PASS" for check in checks)
    print_report(checks=checks, deployment_ready=deployment_ready, loaded_env_file=loaded_env_file)
    return 1 if args.strict and not deployment_ready else 0


def build_checks() -> list[Check]:
    checks: list[Check] = []
    checks.extend(_auth_checks())
    checks.extend(_database_checks())
    checks.extend(_export_root_checks())
    checks.extend(_placeholder_checks())
    checks.extend(_release_artifact_checks())
    checks.extend(_documentation_checks())
    return checks


def print_report(
    *,
    checks: Iterable[Check],
    deployment_ready: bool,
    loaded_env_file: Path | None = None,
) -> None:
    checks = list(checks)
    counts = {status: sum(1 for check in checks if check.status == status) for status in ("PASS", "WARN", "FAIL")}
    print("CivicClerk deployment readiness preflight")
    print(f"Version: civicclerk {__version__}; civiccore {CIVICCORE_VERSION}")
    if loaded_env_file is not None:
        print(f"env_file={_display_path(loaded_env_file)}")
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


def _placeholder_checks() -> list[Check]:
    env_names = (
        STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
        *DATABASE_ENV_VARS,
        "CIVICCLERK_EXPORT_ROOT",
        DIST_ROOT_ENV_VAR,
    )
    placeholder_names = [
        name
        for name in env_names
        if _looks_like_placeholder(os.environ.get(name, ""))
    ]
    if not placeholder_names:
        return [
            Check(
                status="PASS",
                name="deployment profile placeholders",
                message="no known placeholder values were found in deployment environment variables.",
                fix="Keep completed deployment profiles out of source control and rotate any copied sample tokens before use.",
            )
        ]
    return [
        Check(
            status="WARN",
            name="deployment profile placeholders",
            message="placeholder values still need replacement in: " + ", ".join(placeholder_names),
            fix="Replace sample tokens, sample database paths, and sample export roots before treating this profile as deployment-ready.",
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


def _load_env_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"Deployment env file not found: {path}")
    if not resolved.is_file():
        raise SystemExit(f"Deployment env file is not a file: {path}")

    for line_number, raw_line in enumerate(resolved.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise SystemExit(f"Invalid env file line {line_number}: expected KEY=VALUE.")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            raise SystemExit(f"Invalid env file line {line_number}: invalid environment variable name.")
        if key in os.environ:
            continue
        os.environ[key] = _parse_env_value(value.strip(), line_number=line_number)
    return resolved


def _parse_env_value(value: str, *, line_number: int) -> str:
    if not value:
        return ""
    if not (value.startswith("'") or value.startswith('"')):
        return value
    try:
        parsed = shlex.split(value, posix=True)
    except ValueError as exc:
        raise SystemExit(f"Invalid env file line {line_number}: {exc}") from exc
    if len(parsed) > 1:
        raise SystemExit(f"Invalid env file line {line_number}: value contains unquoted whitespace.")
    return parsed[0] if parsed else ""


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "replace-with",
            "replace_me",
            "placeholder",
            "civicclerk-data",
            "civicclerk-exports",
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
