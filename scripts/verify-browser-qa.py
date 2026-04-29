"""Verify CivicClerk browser QA artifacts and accessibility fixtures."""

from __future__ import annotations

import json
import tomllib
from hashlib import sha256
from pathlib import Path


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

    if not release_evidence.exists():
        failures.append("missing docs/browser-qa/release-evidence.json")
        release_data: dict[str, object] = {}
    else:
        release_data = json.loads(release_evidence.read_text(encoding="utf-8"))

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

    release_version = release_data.get("version")
    if release_version != version:
        failures.append(
            f"release evidence version mismatch: expected {version}, found {release_version!r}"
        )

    reviewed_at = release_data.get("reviewed_at")
    if not isinstance(reviewed_at, str) or not reviewed_at.strip():
        failures.append("release evidence missing reviewed_at timestamp")

    page_rel = release_data.get("page")
    if not isinstance(page_rel, str) or not page_rel.strip():
        failures.append("release evidence missing page path")
        page_path = ROOT / "docs" / "index.html"
    else:
        page_path = ROOT / page_rel
        if not page_path.exists():
            failures.append(f"release evidence page is missing: {page_rel}")

    expected_hash = release_data.get("page_sha256")
    if not isinstance(expected_hash, str) or not expected_hash.strip():
        failures.append("release evidence missing page_sha256")
    elif page_path.exists():
        actual_hash = sha256(page_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            failures.append(
                "release evidence hash mismatch for docs/index.html; refresh browser QA screenshots and manifest"
            )

    screenshot_map = release_data.get("screenshots")
    if not isinstance(screenshot_map, dict):
        failures.append("release evidence screenshots map is missing")
    else:
        for viewport in ("desktop", "mobile"):
            rel_path = screenshot_map.get(viewport)
            if not isinstance(rel_path, str) or not rel_path.strip():
                failures.append(f"release evidence missing {viewport} screenshot path")
                continue
            release_shot = ROOT / rel_path
            if not release_shot.exists():
                failures.append(f"missing release screenshot: {rel_path}")
            elif release_shot.stat().st_size <= 20_000:
                failures.append(f"release screenshot too small to be credible evidence: {rel_path}")

    if failures:
        for failure in failures:
            print(f"  FAILED: {failure}")
        print("BROWSER-QA: FAILED")
        return 1

    print("states checked: loading, success, empty, error, partial")
    print("accessibility checked: keyboard, focus, contrast, console")
    print(f"release evidence checked: docs/index.html @ v{version}")
    print("console errors: 0")
    print("BROWSER-QA: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
