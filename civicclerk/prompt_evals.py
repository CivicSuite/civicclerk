"""Offline prompt evaluation harness for CivicClerk prompt YAML files."""

from __future__ import annotations

from dataclasses import dataclass

from civicclerk.prompt_library import load_prompt, render_prompt


@dataclass(frozen=True)
class PromptEvalResult:
    prompt_reference: str
    provider: str
    offline: bool
    passed: bool
    message: str


def run_prompt_evaluations(
    *,
    provider: str,
    offline: bool,
) -> list[PromptEvalResult]:
    """Run deterministic prompt checks without contacting external networks."""
    prompt = load_prompt("minutes_draft")
    rendered = render_prompt(
        prompt,
        {
            "meeting_title": "Budget Hearing",
            "source_materials": "- src-1: Staff report recommends adoption.",
            "drafting_instructions": "Draft concise minutes in neutral clerk language.",
        },
    )

    missing_phrases = [
        phrase
        for evaluation in prompt.evaluations
        for phrase in evaluation.required_phrases
        if phrase not in rendered
    ]
    provider_ok = provider == prompt.provider
    passed = not missing_phrases and provider_ok and offline
    if passed:
        message = "required prompt policy phrases present"
    elif missing_phrases:
        message = "missing required phrases: " + ", ".join(missing_phrases)
    elif not provider_ok:
        message = f"expected provider={prompt.provider}, got provider={provider}"
    else:
        message = "offline evaluation mode is required"

    return [
        PromptEvalResult(
            prompt_reference=prompt.reference,
            provider=provider,
            offline=offline,
            passed=passed,
            message=message,
        )
    ]


__all__ = ["PromptEvalResult", "run_prompt_evaluations"]
