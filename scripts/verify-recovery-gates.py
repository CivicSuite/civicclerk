"""Verify CivicMeetings recovery gates that prevent release-status overclaiming."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    public_docs = {
        "README.md": _read("README.md"),
        "README.txt": _read("README.txt"),
        "USER-MANUAL.md": _read("USER-MANUAL.md"),
        "USER-MANUAL.txt": _read("USER-MANUAL.txt"),
        "docs/index.html": _read("docs/index.html"),
    }
    required_truth = [
        "provisional",
        "recovery gates",
        "not product-ready",
        "mock validation",
        "production deployment",
    ]
    for path, text in public_docs.items():
        lowered = text.lower()
        for phrase in required_truth:
            if phrase not in lowered:
                failures.append(f"{path} missing recovery truth phrase: {phrase}")

    if _read("README.md") != _read("README.txt"):
        failures.append("README.md and README.txt drift")
    if _read("USER-MANUAL.md") != _read("USER-MANUAL.txt"):
        failures.append("USER-MANUAL.md and USER-MANUAL.txt drift")

    package = json.loads(_read("frontend/package.json"))
    if package.get("scripts", {}).get("test:e2e") != "playwright test":
        failures.append("frontend/package.json missing test:e2e Playwright script")
    if not (ROOT / "frontend" / "playwright.config.ts").exists():
        failures.append("missing frontend/playwright.config.ts")
    e2e_specs = sorted((ROOT / "frontend" / "e2e").glob("*.spec.ts"))
    if not e2e_specs:
        failures.append("missing tracked frontend/e2e Playwright specs")

    ci = _read(".github/workflows/ci.yml")
    for phrase in (
        "Verify recovery gates",
        "Run Playwright user flows",
        "Run secret scan",
    ):
        if phrase not in ci:
            failures.append(f"CI missing step: {phrase}")

    release_gate = _read("scripts/verify-release.sh")
    for phrase in (
        "scripts/verify-recovery-gates.py",
        "scripts/verify-secret-scan.py",
        "npm run test:e2e",
        "RUNTIME-INSTALL-PROOF: PASSED",
    ):
        if phrase not in release_gate:
            failures.append(f"verify-release.sh missing gate: {phrase}")

    git_result = subprocess.run(
        ["git", "ls-files", "frontend/e2e", "frontend/playwright.config.ts"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = set(git_result.stdout.splitlines())
    if "frontend/playwright.config.ts" not in tracked:
        failures.append("Playwright config is not tracked by git")
    if not any(path.startswith("frontend/e2e/") for path in tracked):
        failures.append("Playwright user-flow spec is not tracked by git")

    if failures:
        print("RECOVERY-GATES: FAILED")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("RECOVERY-GATES: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
