"""Verify CivicClerk browser QA artifacts and accessibility fixtures."""

from __future__ import annotations

import tomllib
import json
from pathlib import Path

from civiccore.verification import validate_release_browser_evidence
from civicclerk.cc7_completeness import CC7_FRONTEND_PAGES, REQUIRED_VIEW_STATES


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
        ROOT / "docs" / "screenshots" / "public-portal-shell-empty-desktop.png",
        ROOT / "docs" / "screenshots" / "public-portal-shell-desktop.png",
        ROOT / "docs" / "screenshots" / "public-portal-shell-mobile.png",
        ROOT / "docs" / "screenshots" / "cc4-member-success-desktop.png",
        ROOT / "docs" / "screenshots" / "cc4-member-success-mobile.png",
        ROOT / "docs" / "screenshots" / "cc4-member-state-loading.png",
        ROOT / "docs" / "screenshots" / "cc4-member-state-empty.png",
        ROOT / "docs" / "screenshots" / "cc4-member-state-error.png",
        ROOT / "docs" / "screenshots" / "cc4-member-state-partial.png",
        ROOT / "docs" / "screenshots" / "cc4-public-success-desktop.png",
        ROOT / "docs" / "screenshots" / "cc4-public-success-mobile.png",
        ROOT / "docs" / "screenshots" / "cc4-public-state-loading.png",
        ROOT / "docs" / "screenshots" / "cc4-public-state-empty.png",
        ROOT / "docs" / "screenshots" / "cc4-public-state-error.png",
        ROOT / "docs" / "screenshots" / "cc4-public-state-partial.png",
        ROOT / "docs" / "screenshots" / "cc4-public-comment-closed-refusal.png",
        ROOT / "docs" / "screenshots" / "cc4-public-closed-session-blocked.png",
        ROOT / "docs" / "screenshots" / "cc4-agenda-routing-signoff-desktop.png",
        ROOT / "docs" / "screenshots" / "cc4-outcomes-seconded-recusal-desktop.png",
        ROOT / "docs" / "screenshots" / "cc4-meeting-cancel-danger-desktop.png",
        ROOT / "docs" / "screenshots" / "cc5-data-model-docs-desktop.png",
        ROOT / "docs" / "screenshots" / "cc5-data-model-docs-mobile.png",
        ROOT / "docs" / "screenshots" / "cc6-prompt-library-docs-desktop.png",
        ROOT / "docs" / "screenshots" / "cc6-prompt-library-docs-mobile.png",
    ]
    milestone13_summary = ROOT / "docs" / "screenshots" / "milestone13-staff-ui-summary.md"
    public_portal_summary = ROOT / "docs" / "screenshots" / "public-portal-shell-summary.md"
    cc4_summary = ROOT / "docs" / "screenshots" / "cc4-workflow-surface-summary.md"
    cc4_evidence = ROOT / "docs" / "browser-qa" / "cc4-workflow-surface-qa-2026-05-06.json"
    cc5_docs_summary = ROOT / "docs" / "screenshots" / "cc5-data-model-docs-summary.md"
    cc5_docs_evidence = ROOT / "docs" / "browser-qa" / "cc5-data-model-docs-qa-2026-05-06.json"
    cc6_docs_summary = ROOT / "docs" / "screenshots" / "cc6-prompt-library-docs-summary.md"
    cc6_docs_evidence = ROOT / "docs" / "browser-qa" / "cc6-prompt-library-docs-qa-2026-05-06.json"
    cc7_summary = ROOT / "docs" / "screenshots" / "cc7-api-frontend-completeness-summary.md"
    cc7_evidence = ROOT / "docs" / "browser-qa" / "cc7-api-frontend-completeness-qa-2026-05-06.json"

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

    if not milestone13_summary.exists():
        failures.append("missing protected staff UI summary: docs/screenshots/milestone13-staff-ui-summary.md")
    else:
        milestone13_text = milestone13_summary.read_text(encoding="utf-8").lower()
        for required_phrase in (
            "trusted-header",
            "local proxy",
            "session probe",
            "write probe",
            "desktop",
            "mobile",
            "console: 0",
        ):
            if required_phrase not in milestone13_text:
                failures.append(
                    "protected staff UI summary missing phrase: "
                    f"{required_phrase}"
                )

    if not public_portal_summary.exists():
        failures.append("missing public portal summary: docs/screenshots/public-portal-shell-summary.md")
    else:
        public_portal_text = public_portal_summary.read_text(encoding="utf-8").lower()
        for required_phrase in (
            "public portal shell",
            "empty state",
            "success state",
            "error state",
            "partial state",
            "keyboard",
            "focus",
            "contrast",
            "console",
            "console_events=0",
            "exceptions=0",
            "mobile",
        ):
            if required_phrase not in public_portal_text:
                failures.append(
                    "public portal summary missing phrase: "
                    f"{required_phrase}"
                )

    if not cc4_summary.exists():
        failures.append("missing CC-4 workflow browser QA summary: docs/screenshots/cc4-workflow-surface-summary.md")
    else:
        cc4_text = cc4_summary.read_text(encoding="utf-8").lower()
        for required_phrase in (
            "cc-4 workflow surface browser qa",
            "loading",
            "success",
            "empty",
            "error",
            "partial",
            "desktop",
            "mobile",
            "keyboard",
            "focus",
            "contrast",
            "refusal path",
            "closed-session blocked path",
            "console errors: 0",
            "exceptions: 0",
            "text check failures: 0",
        ):
            if required_phrase not in cc4_text:
                failures.append(f"CC-4 workflow QA summary missing phrase: {required_phrase}")

    if not cc4_evidence.exists():
        failures.append("missing CC-4 workflow browser QA evidence: docs/browser-qa/cc4-workflow-surface-qa-2026-05-06.json")
    else:
        evidence = json.loads(cc4_evidence.read_text(encoding="utf-8"))
        totals = evidence.get("totals", {})
        if totals.get("consoleErrors") != 0:
            failures.append("CC-4 workflow QA evidence reports console errors")
        if totals.get("exceptions") != 0:
            failures.append("CC-4 workflow QA evidence reports runtime exceptions")
        if totals.get("textCheckFailures") != 0:
            failures.append("CC-4 workflow QA evidence reports failed visible-text checks")
        if totals.get("minContrast", 0) < 4.5:
            failures.append("CC-4 workflow QA evidence reports sampled contrast below 4.5")
        case_names = {case.get("name") for case in evidence.get("cases", [])}
        for required_case in (
            "member-success-desktop",
            "member-success-mobile",
            "member-loading-desktop",
            "member-empty-desktop",
            "member-error-desktop",
            "member-partial-desktop",
            "public-success-desktop",
            "public-success-mobile",
            "public-loading-desktop",
            "public-empty-desktop",
            "public-error-desktop",
            "public-partial-desktop",
            "public-comment-refusal-desktop",
            "public-closed-session-blocked-desktop",
            "agenda-routing-signoff-desktop",
            "outcomes-seconded-recusal-desktop",
            "meeting-cancel-danger-desktop",
        ):
            if required_case not in case_names:
                failures.append(f"CC-4 workflow QA evidence missing case: {required_case}")

    if not cc5_docs_summary.exists():
        failures.append("missing CC-5 docs browser QA summary: docs/screenshots/cc5-data-model-docs-summary.md")
    else:
        cc5_docs_text = cc5_docs_summary.read_text(encoding="utf-8").lower()
        for required_phrase in (
            "cc-5 data model docs browser qa",
            "docs/index.html",
            "console errors: 0",
            "exceptions: 0",
            "text check failures: 0",
            "docs-desktop",
            "docs-mobile",
        ):
            if required_phrase not in cc5_docs_text:
                failures.append(f"CC-5 docs QA summary missing phrase: {required_phrase}")

    if not cc5_docs_evidence.exists():
        failures.append("missing CC-5 docs browser QA evidence: docs/browser-qa/cc5-data-model-docs-qa-2026-05-06.json")
    else:
        evidence = json.loads(cc5_docs_evidence.read_text(encoding="utf-8"))
        totals = evidence.get("totals", {})
        if totals.get("consoleErrors") != 0:
            failures.append("CC-5 docs QA evidence reports console errors")
        if totals.get("exceptions") != 0:
            failures.append("CC-5 docs QA evidence reports runtime exceptions")
        if totals.get("textCheckFailures") != 0:
            failures.append("CC-5 docs QA evidence reports failed visible-text checks")
        case_names = {case.get("name") for case in evidence.get("cases", [])}
        for required_case in ("docs-desktop", "docs-mobile"):
            if required_case not in case_names:
                failures.append(f"CC-5 docs QA evidence missing case: {required_case}")

    if not cc6_docs_summary.exists():
        failures.append("missing CC-6 docs browser QA summary: docs/screenshots/cc6-prompt-library-docs-summary.md")
    else:
        cc6_docs_text = cc6_docs_summary.read_text(encoding="utf-8").lower()
        for required_phrase in (
            "cc-6 prompt library docs browser qa",
            "docs/index.html",
            "console errors: 0",
            "exceptions: 0",
            "text check failures: 0",
            "keyboard failures: 0",
            "focus failures: 0",
            "horizontal overflow failures: 0",
            "docs-desktop",
            "docs-mobile",
            "clerk-and-attorney approval ceremony",
        ):
            if required_phrase not in cc6_docs_text:
                failures.append(f"CC-6 docs QA summary missing phrase: {required_phrase}")

    if not cc6_docs_evidence.exists():
        failures.append("missing CC-6 docs browser QA evidence: docs/browser-qa/cc6-prompt-library-docs-qa-2026-05-06.json")
    else:
        evidence = json.loads(cc6_docs_evidence.read_text(encoding="utf-8"))
        totals = evidence.get("totals", {})
        if totals.get("consoleErrors") != 0:
            failures.append("CC-6 docs QA evidence reports console errors")
        if totals.get("exceptions") != 0:
            failures.append("CC-6 docs QA evidence reports runtime exceptions")
        if totals.get("textCheckFailures") != 0:
            failures.append("CC-6 docs QA evidence reports failed visible-text checks")
        if totals.get("keyboardFailures") != 0:
            failures.append("CC-6 docs QA evidence reports keyboard failures")
        if totals.get("focusFailures") != 0:
            failures.append("CC-6 docs QA evidence reports focus failures")
        if totals.get("horizontalOverflowFailures") != 0:
            failures.append("CC-6 docs QA evidence reports horizontal overflow")
        if totals.get("minContrast", 0) < 4.5:
            failures.append("CC-6 docs QA evidence reports sampled contrast below 4.5")
        case_names = {case.get("name") for case in evidence.get("cases", [])}
        for required_case in ("docs-desktop", "docs-mobile"):
            if required_case not in case_names:
                failures.append(f"CC-6 docs QA evidence missing case: {required_case}")

    if not cc7_summary.exists():
        failures.append("missing CC-7 API/frontend browser QA summary: docs/screenshots/cc7-api-frontend-completeness-summary.md")
    else:
        cc7_summary_text = cc7_summary.read_text(encoding="utf-8").lower()
        for required_phrase in (
            "cc-7 api and frontend completeness browser qa",
            "20 pages",
            "5 states",
            "desktop",
            "mobile",
            "keyboard failures: 0",
            "focus failures: 0",
            "horizontal overflow failures: 0",
        ):
            if required_phrase not in cc7_summary_text:
                failures.append(f"CC-7 browser QA summary missing phrase: {required_phrase}")

    if not cc7_evidence.exists():
        failures.append("missing CC-7 API/frontend browser QA evidence: docs/browser-qa/cc7-api-frontend-completeness-qa-2026-05-06.json")
    else:
        evidence = json.loads(cc7_evidence.read_text(encoding="utf-8"))
        totals = evidence.get("totals", {})
        if totals.get("consoleErrors") != 0:
            failures.append("CC-7 browser QA evidence reports console errors")
        if totals.get("exceptions") != 0:
            failures.append("CC-7 browser QA evidence reports runtime exceptions")
        if totals.get("textCheckFailures") != 0:
            failures.append("CC-7 browser QA evidence reports failed visible-text checks")
        if totals.get("keyboardFailures") != 0:
            failures.append("CC-7 browser QA evidence reports keyboard failures")
        if totals.get("focusFailures") != 0:
            failures.append("CC-7 browser QA evidence reports focus failures")
        if totals.get("horizontalOverflowFailures") != 0:
            failures.append("CC-7 browser QA evidence reports horizontal overflow")
        if totals.get("minContrast", 0) < 4.5:
            failures.append("CC-7 browser QA evidence reports sampled contrast below 4.5")
        case_keys = {
            (case.get("page"), case.get("state"), case.get("viewport"))
            for case in evidence.get("cases", [])
        }
        for page in CC7_FRONTEND_PAGES:
            for state in REQUIRED_VIEW_STATES:
                for viewport in ("desktop", "mobile"):
                    if (page.id, state, viewport) not in case_keys:
                        failures.append(
                            "CC-7 browser QA evidence missing case: "
                            f"{page.id}-{state}-{viewport}"
                        )
        for case in evidence.get("cases", []):
            screenshot = case.get("screenshot")
            if screenshot:
                screenshot_path = ROOT / str(screenshot)
                if not screenshot_path.exists():
                    failures.append(f"CC-7 browser QA evidence screenshot missing: {screenshot}")
                elif screenshot_path.stat().st_size <= 20_000:
                    failures.append(f"CC-7 browser QA evidence screenshot too small: {screenshot}")

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
