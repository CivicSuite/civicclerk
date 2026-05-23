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
EXPECTED_PROMPTS = {
    "agenda_item_summary",
    "staff_report_normalizer",
    "packet_completeness_reviewer",
    "notice_compliance_reviewer",
    "motion_vote_summary",
    "minutes_draft",
    "ordinance_resolution_extractor",
    "closed_session_safe_summarizer",
    "public_plain_language_meeting_explainer",
}


@pytest.mark.asyncio
async def test_all_spec_prompts_are_versioned_and_resolve_through_civiccore() -> None:
    from civicclerk.prompt_library import (
        CONSUMER_APP,
        PromptLibraryError,
        list_prompt_ids,
        list_prompts,
        load_prompt,
        render_prompt,
        resolve_prompt_template,
    )

    assert set(list_prompt_ids()) == EXPECTED_PROMPTS
    prompts = list_prompts()
    assert {prompt.id for prompt in prompts} == EXPECTED_PROMPTS

    for prompt in prompts:
        resolved = await resolve_prompt_template(prompt.id)
        assert resolved.consumer_app == CONSUMER_APP
        assert resolved.template_name == prompt.id
        assert resolved.is_override is True
        assert resolved.user_prompt_template == prompt.template
        assert resolved.system_prompt == prompt.system_prompt
        assert resolved.version == prompt.resolver_version
        assert prompt.version == "0.1.0"
        assert prompt.provider == "ollama"
        assert prompt.required_variables
        assert prompt.evaluations

    public_prompts = {prompt.id: prompt for prompt in prompts if prompt.public_facing}
    assert set(public_prompts) == {
        "closed_session_safe_summarizer",
        "public_plain_language_meeting_explainer",
    }
    for prompt in public_prompts.values():
        assert prompt.approval_required == "clerk_and_attorney"

    with pytest.raises(PromptLibraryError, match="source_materials"):
        render_prompt(load_prompt("minutes_draft"), {"meeting_title": "Budget Hearing"})


def test_minutes_prompt_yaml_remains_renderable_and_actionable() -> None:
    from civicclerk.prompt_library import load_prompt, render_prompt

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


def test_civiccore_prompt_resolver_import_does_not_pollute_civicclerk_metadata() -> None:
    import civicclerk.prompt_library  # noqa: F401
    from civicclerk import models

    assert "prompt_templates" not in models.Base.metadata.tables
    assert "model_registry" not in models.Base.metadata.tables
    assert all(
        table.schema in {None, "civicclerk", "public"}
        for table in models.Base.metadata.tables.values()
    )


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
    for prompt_id in EXPECTED_PROMPTS:
        assert f"{prompt_id}@0.1.0" in result.stdout
    assert "provider=ollama" in result.stdout
    assert "offline=true" in result.stdout
    assert "resolver, policy phrases, approval gate, and mutation stability passed" in result.stdout


def test_prompt_eval_module_cli_runs_the_same_offline_gate() -> None:
    env = os.environ.copy()
    env["CIVICCORE_LLM_PROVIDER"] = "ollama"
    env["CIVICCLERK_EVAL_OFFLINE"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "civicclerk.prompt_evals"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PROMPT-EVALS: PASSED" in result.stdout
    assert "consumer_app" not in result.stderr


def test_ci_runs_prompt_eval_harness_before_merge() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "Run prompt eval harness" in workflow
    assert "CIVICCORE_LLM_PROVIDER: ollama" in workflow
    assert "CIVICCLERK_EVAL_OFFLINE: \"1\"" in workflow
    assert "python scripts/run-prompt-evals.py" in workflow


def test_policy_bearing_prompt_strings_live_only_in_yaml_not_runtime() -> None:
    yaml_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "prompts").glob("*.yaml"))
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "civicclerk").glob("*.py")
        if path.name not in {"prompt_library.py", "__init__.py"}
    )

    for phrase in PROMPT_POLICY_PHRASES:
        assert phrase in yaml_text
        assert phrase not in runtime_text


def test_prompt_eval_harness_uses_civiccore_resolver_not_standalone_rendering() -> None:
    eval_text = (ROOT / "civicclerk" / "prompt_evals.py").read_text(encoding="utf-8")
    library_text = (ROOT / "civicclerk" / "prompt_library.py").read_text(encoding="utf-8")

    assert "resolve_prompt_template_sync" in eval_text
    assert "resolve_template(" in library_text
    assert 'consumer_app=CONSUMER_APP' in library_text


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
    assert "civiccore.llm.resolve_template" in docs
    assert 'consumer_app="civicclerk"' in docs
    assert "clerk-and-attorney approval ceremony" in docs
    assert "legal-determination refusal" in docs
    normalized_docs = docs.replace("-", " ").replace("/", " ")
    for prompt_id in EXPECTED_PROMPTS:
        assert prompt_id.replace("_", " ") in normalized_docs or prompt_id in docs
    assert "connectors shipped" not in docs
    assert "full ui shipped" not in docs
