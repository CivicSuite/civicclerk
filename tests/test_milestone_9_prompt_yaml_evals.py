"""Milestone 9 prompt YAML library and evaluation harness contract."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app


ROOT = Path(__file__).resolve().parents[1]
PROMPT_POLICY_PHRASES = [
    "Draft official meeting minutes",
    "Every material sentence must include citations",
    "Never adopt or publicly post minutes automatically",
]


def test_minutes_prompt_yaml_is_versioned_renderable_and_actionable() -> None:
    from civicclerk.prompt_library import PromptLibraryError, load_prompt, render_prompt

    prompt = load_prompt("minutes_draft")

    assert prompt.id == "minutes_draft"
    assert prompt.version == "0.1.0"
    assert prompt.provider == "ollama"
    assert prompt.required_variables == (
        "meeting_title",
        "source_materials",
        "drafting_instructions",
    )
    rendered = render_prompt(
        prompt,
        {
            "meeting_title": "Budget Hearing",
            "source_materials": "- src-1: Staff report",
            "drafting_instructions": "Use neutral clerk language.",
        },
    )

    assert "Budget Hearing" in rendered
    assert "src-1" in rendered
    assert "Every material sentence must include citations" in rendered

    with pytest.raises(PromptLibraryError, match="source_materials"):
        render_prompt(prompt, {"meeting_title": "Budget Hearing"})


@pytest.mark.asyncio
async def test_minutes_draft_api_requires_prompt_version_from_yaml_library() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Budget Hearing",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
                "created_by": "clerk@example.gov",
            },
        )
        meeting_id = meeting.json()["id"]
        payload = {
            "model": "gemma4:local",
            "prompt_version": "ad-hoc-copy-paste",
            "human_approver": "clerk@example.gov",
            "source_materials": [
                {
                    "source_id": "src-1",
                    "label": "Staff report",
                    "text": "The staff report recommends adoption.",
                }
            ],
            "sentences": [
                {
                    "text": "The council reviewed the staff report.",
                    "citations": ["src-1"],
                }
            ],
        }

        rejected = await client.post(f"/meetings/{meeting_id}/minutes/drafts", json=payload)
        assert rejected.status_code == 422
        assert rejected.json()["detail"] == {
            "message": "Minutes drafts must use a prompt version from the CivicClerk YAML prompt library.",
            "fix": "Use prompt_version 'minutes_draft@0.1.0' or another version returned by the prompt library.",
        }

        payload["prompt_version"] = "minutes_draft@0.1.0"
        accepted = await client.post(f"/meetings/{meeting_id}/minutes/drafts", json=payload)
        assert accepted.status_code == 201
        assert accepted.json()["provenance"]["prompt_version"] == "minutes_draft@0.1.0"


def test_prompt_eval_harness_runs_offline_with_ollama_provider_selected() -> None:
    env = os.environ.copy()
    env["CIVICCORE_LLM_PROVIDER"] = "ollama"
    env["CIVICCLERK_EVAL_OFFLINE"] = "1"
    env["NO_NETWORK"] = "1"

    result = subprocess.run(
        [sys.executable, "scripts/run-prompt-evals.py"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PROMPT-EVALS: PASSED" in result.stdout
    assert "minutes_draft@0.1.0" in result.stdout
    assert "provider=ollama" in result.stdout
    assert "offline=true" in result.stdout


def test_ci_runs_prompt_eval_harness_before_merge() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "Run prompt eval harness" in workflow
    assert "CIVICCORE_LLM_PROVIDER: ollama" in workflow
    assert "CIVICCLERK_EVAL_OFFLINE: \"1\"" in workflow
    assert "python scripts/run-prompt-evals.py" in workflow


def test_policy_bearing_prompt_strings_live_only_in_yaml_not_runtime() -> None:
    yaml_text = (ROOT / "prompts" / "minutes_draft.yaml").read_text(encoding="utf-8")
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "civicclerk").glob("*.py")
        if path.name not in {"prompt_library.py", "__init__.py"}
    )

    for phrase in PROMPT_POLICY_PHRASES:
        assert phrase in yaml_text
        assert phrase not in runtime_text


def test_docs_record_prompt_yaml_eval_scope_without_claiming_connectors_or_ui() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    ).lower()

    assert "prompt yaml" in docs
    assert "evaluation harness" in docs
    assert "outbound network blocked" in docs
    assert "connectors shipped" not in docs
    assert "full ui shipped" not in docs
