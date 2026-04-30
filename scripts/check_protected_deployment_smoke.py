"""Run protected CivicClerk deployment smoke probes from an env profile."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx

from civicclerk.main import STAFF_AUTH_TOKEN_ROLES_ENV_VAR, app
from scripts.check_deployment_readiness import _load_env_file, build_checks


ROOT = Path(__file__).resolve().parents[1]


def _redacted_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            redacted[key] = "Bearer <redacted>"
        else:
            redacted[key] = value
    return redacted


def _deployment_ready() -> tuple[bool, list[str]]:
    checks = build_checks()
    failures = [
        f"{check.status} {check.name}: {check.message}"
        for check in checks
        if check.status != "PASS"
    ]
    return not failures, failures


def _first_bearer_token() -> str | None:
    raw = os.environ.get(STAFF_AUTH_TOKEN_ROLES_ENV_VAR, "").strip()
    if not raw:
        return None
    try:
        token_map = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(token_map, dict):
        return None
    for token in token_map:
        if isinstance(token, str) and token:
            return token
    return None


def _resolve_probe_headers(probe: dict[str, Any]) -> dict[str, str]:
    headers = {
        str(key): str(value)
        for key, value in dict(probe.get("headers", {})).items()
    }
    authorization = headers.get("Authorization")
    if authorization and "<configured token>" in authorization:
        token = _first_bearer_token()
        if token is None:
            raise RuntimeError(
                "Readiness returned a bearer probe but no token could be selected from "
                f"{STAFF_AUTH_TOKEN_ROLES_ENV_VAR}."
            )
        headers["Authorization"] = authorization.replace("<configured token>", token)
    return headers


async def _run_smoke(*, base_url: str, proxy_client_ip: str) -> int:
    transport = httpx.ASGITransport(app=app, client=(proxy_client_ip, 443))
    async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
        health = await client.get("/health")
        readiness = await client.get("/staff/auth-readiness")

        if health.status_code != 200:
            print(f"[FAIL] health: expected 200, got {health.status_code}")
            print("Fix: start the CivicClerk app from the same env profile and retry.")
            return 1
        if readiness.status_code != 200:
            print(f"[FAIL] auth readiness: expected 200, got {readiness.status_code}")
            print("Fix: run python scripts/check_deployment_readiness.py --env-file <profile> --strict first.")
            return 1

        readiness_payload = readiness.json()
        if readiness_payload.get("deployment_ready") is not True:
            print("[FAIL] auth readiness: deployment_ready is not true")
            print(f"Fix: {readiness_payload.get('fix', 'Complete protected auth configuration and retry.')}")
            return 1

        session_probe = dict(readiness_payload.get("session_probe") or {})
        write_probe = dict(readiness_payload.get("write_probe") or {})
        session_headers = _resolve_probe_headers(session_probe)
        write_headers = _resolve_probe_headers(write_probe)

        session = await client.request(
            str(session_probe.get("method", "GET")),
            str(session_probe.get("path", "/staff/session")),
            headers=session_headers,
        )
        write = await client.request(
            str(write_probe.get("method", "POST")),
            str(write_probe.get("path", "/agenda-intake")),
            headers=write_headers,
            json=write_probe.get("body"),
        )

    print("CivicClerk protected deployment smoke")
    print(f"[PASS] health: {health.status_code}")
    print(f"[PASS] auth readiness: mode={readiness_payload.get('mode')} deployment_ready=true")
    print(f"[INFO] session headers: {_redacted_headers(session_headers)}")
    if session.status_code != 200:
        print(f"[FAIL] session probe: expected 200, got {session.status_code}")
        print("Fix: confirm the token or trusted-header identity has a permitted staff role.")
        return 1
    print("[PASS] session probe: 200")
    print(f"[INFO] write headers: {_redacted_headers(write_headers)}")
    if write.status_code != 201:
        print(f"[FAIL] write probe: expected 201, got {write.status_code}")
        print("Fix: run the session probe first, then confirm staff write authorization and persistent stores.")
        return 1
    print("[PASS] write probe: 201")
    print("PROTECTED-DEPLOYMENT-SMOKE: PASSED")
    return 0


def _print_plan(env_file: Path, *, base_url: str, proxy_client_ip: str) -> None:
    print("CivicClerk protected deployment smoke")
    print(f"Env profile: {env_file}")
    print(f"Base URL: {base_url}")
    print(f"Trusted-header in-process client IP: {proxy_client_ip}")
    print("Steps:")
    print("  1. Load the env profile without printing token or database values.")
    print("  2. Run strict deployment readiness checks.")
    print("  3. GET /health.")
    print("  4. GET /staff/auth-readiness.")
    print("  5. Execute the returned protected session probe.")
    print("  6. Execute the returned protected write probe.")
    print("Fix path: replace profile placeholders, configure protected staff auth, and rerun.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run protected deployment smoke probes from an env profile.")
    parser.add_argument("--env-file", required=True, help="Completed deployment env profile to load.")
    parser.add_argument("--base-url", default="http://testserver", help="Base URL label for in-process smoke checks.")
    parser.add_argument(
        "--trusted-proxy-client-ip",
        default="127.0.0.1",
        help="Client IP used by the in-process ASGI smoke check for trusted-header profiles.",
    )
    parser.add_argument("--print-only", action="store_true", help="Print the smoke plan without running probes.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_file = _load_env_file(Path(args.env_file))
    if args.print_only:
        _print_plan(env_file, base_url=args.base_url, proxy_client_ip=args.trusted_proxy_client_ip)
        return 0

    deployment_ready, failures = _deployment_ready()
    if not deployment_ready:
        print("CivicClerk protected deployment smoke")
        for failure in failures:
            print(f"[FAIL] readiness: {failure}")
        print("Fix: complete the deployment env profile and rerun check_deployment_readiness.py --strict first.")
        print("PROTECTED-DEPLOYMENT-SMOKE: FAILED")
        return 1

    return asyncio.run(_run_smoke(base_url=args.base_url, proxy_client_ip=args.trusted_proxy_client_ip))


if __name__ == "__main__":
    raise SystemExit(main())
