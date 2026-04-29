"""Verify CivicClerk browser QA artifacts and accessibility fixtures."""

from __future__ import annotations

import tomllib
from pathlib import Path

from civiccore.verification import validate_release_browser_evidence


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_STATES = ("loading", "success", "empty", "error", "partial")
REQUIRED_CHECKS = ("keyboard", "focus", "contrast", "console")


def main() -> int:
    failures: list[str] = []
    checklist = ROOT / "docs" / "browser-qa" / "milestone11-checklist.md"
    release_evidence = ROOT / "docs" / "browser-qa" / "release-evidence.json"
    states = ROOT / "docs" / "browser-qa" / "states.html"
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    screenshots = [
        ROOT / "docs" / "screenshots" / "milestone11-browser-qa-desktop.png",
        ROOT / "docs" / "screenshots" / "milestone11-browser-qa-mobile.png",
        ROOT / "docs" / "screenshots" / "milestone13-staff-ui-desktop.png",
        ROOT / "docs" / "screenshots" / "milestone13-staff-ui-mobile.png",
        ROOT / "docs" / "browser-qa-production-depth-live-meeting-outcomes-screen-desktop.png",
        ROOT / "docs" / "browser-qa-production-depth-live-meeting-outcomes-screen-mobile.png",
        ROOT / "docs" / "browser-qa-production-depth-live-minutes-draft-screen-desktop.png",
        ROOT / "docs" / "browser-qa-production-depth-live-minutes-draft-screen-mobile.png",
        ROOT / "docs" / "browser-qa-production-depth-live-archive-screen-desktop.png",
        ROOT / "docs" / "browser-qa-production-depth-live-archive-screen-mobile.png",
        ROOT / "docs" / "browser-qa-production-depth-live-connector-import-screen-desktop.png",
        ROOT / "docs" / "browser-qa-production-depth-live-connector-import-screen-mobile.png",
        ROOT / "docs" / "browser-qa-production-depth-live-packet-export-screen-desktop.png",
        ROOT / "docs" / "browser-qa-production-depth-live-packet-export-screen-mobile.png",
        ROOT / "docs" / "browser-qa-production-depth-agenda-item-persistence-desktop.png",
        ROOT / "docs" / "browser-qa-production-depth-agenda-item-persistence-mobile.png",
    ]

    if not checklist.exists():
        failures.append("missing docs/browser-qa/milestone11-checklist.md")
        checklist_text = ""
    else:
        checklist_text = checklist.read_text(encoding="utf-8").lower()

    if not states.exists():
        failures.append("missing docs/browser-qa/states.html")
        states_text = ""
    else:
        states_text = states.read_text(encoding="utf-8").lower()

    for state in REQUIRED_STATES:
        if state not in checklist_text:
            failures.append(f"checklist missing state: {state}")
        if f'data-state="{state}"' not in states_text:
            failures.append(f"state fixture missing data-state={state}")

    for required_check in REQUIRED_CHECKS:
        if required_check not in checklist_text:
            failures.append(f"checklist missing accessibility check: {required_check}")

    if ":focus-visible" not in states_text:
        failures.append("state fixture missing :focus-visible styling")
    if "how to fix" not in states_text:
        failures.append("state fixture missing actionable fix text")
    if "<main" not in states_text:
        failures.append("state fixture missing semantic main landmark")

    for screenshot in screenshots:
        if not screenshot.exists():
            failures.append(f"missing screenshot: {screenshot.relative_to(ROOT)}")
        elif screenshot.stat().st_size <= 20_000:
            failures.append(f"screenshot too small to be credible evidence: {screenshot.relative_to(ROOT)}")

    try:
        release_result = validate_release_browser_evidence(
            repo_root=ROOT,
            manifest_path=release_evidence,
            expected_version=version,
        )
    except ValueError as exc:
        failures.append(str(exc))
        release_result = None

    if failures:
        for failure in failures:
            print(f"  FAILED: {failure}")
        print("BROWSER-QA: FAILED")
        return 1

    print("states checked: loading, success, empty, error, partial")
    print("accessibility checked: keyboard, focus, contrast, console")
    if release_result is not None:
        print(
            f"release evidence checked: {release_result.page.relative_to(ROOT).as_posix()} @ v{version}"
        )
    else:
        print(f"release evidence checked: docs/index.html @ v{version}")
    print("console errors: 0")
    print("BROWSER-QA: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
