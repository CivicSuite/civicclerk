"""Verify optional downstream Windows installer signing inputs without signing."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "1.0.1"
DEFAULT_ARTIFACT = Path("installer/windows/build") / f"CivicClerk-{DEFAULT_VERSION}-Setup.exe"
SIGNTOOL_ENV_VARS = ("CIVICCLERK_SIGNTOOL_PATH", "SIGNTOOL")
SHA1_ENV_VAR = "CIVICCLERK_SIGNING_CERT_SHA1"
PFX_ENV_VAR = "CIVICCLERK_SIGNING_PFX"
PFX_PASSWORD_ENV_VAR = "CIVICCLERK_SIGNING_PFX_PASSWORD_ENV"
TIMESTAMP_ENV_VAR = "CIVICCLERK_SIGNING_TIMESTAMP_URL"
WINDOWS_KITS_BIN = Path("C:/Program Files (x86)/Windows Kits/10/bin")


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


def _signtool_path() -> str | None:
    for env_var in SIGNTOOL_ENV_VARS:
        configured = os.environ.get(env_var, "").strip()
        if configured:
            return configured if Path(configured).exists() else shutil.which(configured)
    path_hit = shutil.which("signtool")
    if path_hit:
        return path_hit
    if WINDOWS_KITS_BIN.exists():
        candidates = sorted(
            WINDOWS_KITS_BIN.glob("*/x64/signtool.exe"),
            key=lambda path: path.parts,
            reverse=True,
        )
        if candidates:
            return str(candidates[0])
    return None


def build_checks(*, artifact: Path) -> list[Check]:
    checks: list[Check] = []
    if artifact.exists():
        checks.append(
            Check(
                status="PASS",
                name="installer artifact",
                message=f"setup executable exists at {_display(artifact)}.",
                fix="Use this exact artifact only if your organization signs an internal downstream build.",
            )
        )
    else:
        checks.append(
            Check(
                status="FAIL",
                name="installer artifact",
                message=f"setup executable is missing: {_display(artifact)}.",
                fix="Run bash installer/windows/build-installer.sh after bash scripts/verify-release.sh.",
            )
        )

    if _signtool_path():
        checks.append(
            Check(
                status="PASS",
                name="signtool",
                message="Microsoft SignTool is configured or available on PATH.",
                fix="Use the same SignTool path if your organization signs an internal downstream build.",
            )
        )
    else:
        checks.append(
            Check(
                status="FAIL",
                name="signtool",
                message="Microsoft SignTool was not found.",
                fix="Install the Windows SDK or set CIVICCLERK_SIGNTOOL_PATH to signtool.exe.",
            )
        )

    sha1 = os.environ.get(SHA1_ENV_VAR, "").strip()
    pfx = os.environ.get(PFX_ENV_VAR, "").strip()
    password_env_name = os.environ.get(PFX_PASSWORD_ENV_VAR, "").strip()
    if sha1:
        checks.append(
            Check(
                status="PASS",
                name="certificate identity",
                message=f"{SHA1_ENV_VAR} is set for certificate-store signing.",
                fix="Confirm the certificate exists in the current user's certificate store before signing.",
            )
        )
    elif pfx:
        if password_env_name and os.environ.get(password_env_name):
            checks.append(
                Check(
                    status="PASS",
                    name="certificate identity",
                    message=f"{PFX_ENV_VAR} and redacted password env {PFX_PASSWORD_ENV_VAR} are configured.",
                    fix="Keep the PFX and password out of git and local logs.",
                )
            )
        else:
            checks.append(
                Check(
                    status="FAIL",
                    name="certificate password",
                    message=f"{PFX_ENV_VAR} is set, but {PFX_PASSWORD_ENV_VAR} does not name a populated password env var.",
                    fix=f"Set {PFX_PASSWORD_ENV_VAR}=MY_SECRET_ENV and put the PFX password in MY_SECRET_ENV.",
                )
            )
    else:
        checks.append(
            Check(
                status="FAIL",
                name="certificate identity",
                message="no code-signing certificate identity is configured.",
                fix=f"Set {SHA1_ENV_VAR} for certificate-store signing, or {PFX_ENV_VAR} plus {PFX_PASSWORD_ENV_VAR} for PFX signing.",
            )
        )

    if os.environ.get(TIMESTAMP_ENV_VAR, "").strip():
        checks.append(
            Check(
                status="PASS",
                name="timestamp authority",
                message=f"{TIMESTAMP_ENV_VAR} is configured.",
                fix="Use a trusted RFC 3161 timestamp service for signed internal builds.",
            )
        )
    else:
        checks.append(
            Check(
                status="FAIL",
                name="timestamp authority",
                message="no timestamp authority URL is configured.",
                fix=f"Set {TIMESTAMP_ENV_VAR} to the organization-approved RFC 3161 timestamp URL.",
            )
        )
    return checks


def _print_report(checks: list[Check]) -> int:
    ready = all(check.status == "PASS" for check in checks)
    print("CivicClerk downstream installer signing readiness")
    print(f"signing_ready={str(ready).lower()}")
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.message}")
        print(f"  fix: {check.fix}")
    print("ENTERPRISE-INSTALLER-SIGNING: PASSED" if ready else "ENTERPRISE-INSTALLER-SIGNING: FAILED")
    return 0 if ready else 1


def _print_plan(artifact: Path) -> None:
    print("CivicClerk downstream installer signing readiness")
    print(f"Artifact: {_display(artifact)}")
    print("Required signing inputs:")
    print(f"  1. {SIGNTOOL_ENV_VARS[0]} or {SIGNTOOL_ENV_VARS[1]} pointing to Microsoft signtool.exe.")
    print(f"  2. {SHA1_ENV_VAR} for certificate-store signing, or {PFX_ENV_VAR} for a PFX file.")
    print(f"  3. If using PFX, set {PFX_PASSWORD_ENV_VAR} to the name of a populated password env var.")
    print(f"  4. {TIMESTAMP_ENV_VAR} with the organization-approved RFC 3161 timestamp URL.")
    print("No secrets are printed. This optional downstream helper verifies readiness; it does not sign the public CivicSuite installer.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify optional downstream installer signing inputs without signing.")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT), help="Setup executable to sign.")
    parser.add_argument("--print-only", action="store_true", help="Print the signing readiness plan.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact = Path(args.artifact)
    if args.print_only:
        _print_plan(artifact)
        return 0
    return _print_report(build_checks(artifact=artifact))


if __name__ == "__main__":
    raise SystemExit(main())
