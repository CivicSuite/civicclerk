"""Milestone 11 accessibility and browser QA gate contract."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_browser_qa_artifacts_cover_required_states_and_accessibility_checks() -> None:
    checklist = ROOT / "docs" / "browser-qa" / "milestone11-checklist.md"
    release_evidence = ROOT / "docs" / "browser-qa" / "release-evidence.json"
    states = ROOT / "docs" / "browser-qa" / "states.html"
    desktop = ROOT / "docs" / "screenshots" / "milestone11-browser-qa-desktop.png"
    mobile = ROOT / "docs" / "screenshots" / "milestone11-browser-qa-mobile.png"
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    release_desktop = ROOT / "docs" / f"browser-qa-v{version}-release-desktop.png"
    release_mobile = ROOT / "docs" / f"browser-qa-v{version}-release-mobile.png"

    assert checklist.exists()
    assert release_evidence.exists()
    assert states.exists()
    assert desktop.exists() and desktop.stat().st_size > 20_000
    assert mobile.exists() and mobile.stat().st_size > 20_000
    assert release_desktop.exists() and release_desktop.stat().st_size > 20_000
    assert release_mobile.exists() and release_mobile.stat().st_size > 20_000

    checklist_text = checklist.read_text(encoding="utf-8").lower()
    states_text = states.read_text(encoding="utf-8").lower()
    for state in ["loading", "success", "empty", "error", "partial"]:
        assert state in checklist_text
        assert f'data-state="{state}"' in states_text
    for check in ["keyboard", "focus", "contrast", "console"]:
        assert check in checklist_text
    assert "how to fix" in states_text
    assert ":focus-visible" in states_text
    assert "<main" in states_text


def test_browser_qa_gate_script_passes_and_reports_checked_states() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/verify-browser-qa.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BROWSER-QA: PASSED" in result.stdout
    assert "states checked: loading, success, empty, error, partial" in result.stdout
    assert "release evidence checked: docs/index.html @ v0.1.14" in result.stdout
    assert "console errors: 0" in result.stdout


def test_ci_runs_browser_qa_gate_before_merge() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "Verify browser QA evidence" in workflow
    assert "python scripts/verify-browser-qa.py" in workflow


def test_landing_page_has_accessible_focus_and_no_console_error_script() -> None:
    landing = (ROOT / "docs" / "index.html").read_text(encoding="utf-8").lower()

    assert ":focus-visible" in landing
    assert "<main" in landing
    assert "aria-label" in landing
    assert "console.error" not in landing


def test_docs_record_browser_qa_gate_without_claiming_full_ui() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    ).lower()

    assert "browser qa" in docs
    assert "keyboard" in docs
    assert "focus" in docs
    assert "contrast" in docs
    assert "console" in docs
    assert "full ui shipped" not in docs
