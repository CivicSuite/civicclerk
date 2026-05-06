"""Offline prompt evaluation harness for CivicClerk prompt YAML files."""

from __future__ import annotations

from dataclasses import dataclass
import os

from civicclerk.prompt_library import (
    list_prompt_ids,
    load_prompt,
    render_prompt_template,
    resolve_prompt_template_sync,
)


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
    return [
        _evaluate_prompt(prompt_id=prompt_id, provider=provider, offline=offline)
        for prompt_id in list_prompt_ids()
    ]


def _evaluate_prompt(*, prompt_id: str, provider: str, offline: bool) -> PromptEvalResult:
    prompt = load_prompt(prompt_id)
    prompt_template = resolve_prompt_template_sync(prompt_id)
    variables = _variables_for(prompt.required_variables)
    rendered = render_prompt_template(
        prompt_template,
        variables,
        prompt.required_variables,
    )
    mutated_variables = dict(variables)
    first_variable = prompt.required_variables[0]
    mutated_variables[first_variable] = f"{variables[first_variable]} MUTATION_SENTINEL"
    mutated_rendered = render_prompt_template(
        prompt_template,
        mutated_variables,
        prompt.required_variables,
    )

    missing_phrases = [
        phrase
        for evaluation in prompt.evaluations
        for phrase in evaluation.required_phrases
        if phrase not in rendered
    ]
    provider_ok = provider == prompt.provider
    resolver_ok = prompt_template.consumer_app == "civicclerk" and prompt_template.template_name == prompt.id
    mutation_ok = "MUTATION_SENTINEL" in mutated_rendered
    approval_ok = not prompt.public_facing or prompt.approval_required == "clerk_and_attorney"
    passed = (
        not missing_phrases
        and provider_ok
        and offline
        and resolver_ok
        and mutation_ok
        and approval_ok
    )
    if passed:
        message = "resolver, policy phrases, approval gate, and mutation stability passed"
    elif missing_phrases:
        message = "missing required phrases: " + ", ".join(missing_phrases)
    elif not provider_ok:
        message = f"expected provider={prompt.provider}, got provider={provider}"
    elif not offline:
        message = "offline evaluation mode is required"
    elif not resolver_ok:
        message = "prompt did not resolve through civiccore.llm for consumer_app=civicclerk"
    elif not mutation_ok:
        message = "prompt input mutation was not reflected in the rendered template"
    else:
        message = "public-facing prompt is missing clerk_and_attorney approval gate"

    return PromptEvalResult(
        prompt_reference=prompt.reference,
        provider=provider,
        offline=offline,
        passed=passed,
        message=message,
    )


def _variables_for(required_variables: tuple[str, ...]) -> dict[str, str]:
    samples = {
        "adopted_items": "- ORD-2026-04: Adopted water conservation ordinance.",
        "agenda_item_id": "AI-001",
        "approved_public_record": "Agenda and adopted minutes approved for public release.",
        "audience_need": "Resident wants a plain-language summary.",
        "department_name": "Planning",
        "draft_report": "Staff recommends approval with conditions.",
        "drafting_instructions": "Draft concise minutes in neutral clerk language.",
        "item_title": "Downtown lighting contract",
        "jurisdiction_rules": "Post regular meeting notice at least 72 hours before start.",
        "meeting_title": "Budget Hearing",
        "meeting_type": "regular",
        "minutes_excerpt": "Council adopted ORD-2026-04 by roll-call vote.",
        "motion_records": "- Motion M-1 seconded by Member Lee.",
        "notice_record": "Posted at City Hall and website with proof hash.",
        "packet_manifest": "- agenda.pdf\n- staff-report.pdf",
        "requested_summary": "Summarize privileged closed-session litigation strategy.",
        "required_items": "- agenda\n- staff report\n- posting proof",
        "source_materials": "- src-1: Staff report recommends adoption.",
        "staff_context": "Department submitted the item for regular agenda placement.",
        "visibility_context": "closed_session",
        "vote_records": "- Member Rivera: aye\n- Member Lee: recusal",
    }
    return {
        variable: samples.get(variable, f"Sample value for {variable}")
        for variable in required_variables
    }


def main() -> int:
    provider = os.environ.get("CIVICCORE_LLM_PROVIDER", "")
    offline = os.environ.get("CIVICCLERK_EVAL_OFFLINE") == "1"
    results = run_prompt_evaluations(provider=provider, offline=offline)

    failures = [result for result in results if not result.passed]
    for result in results:
        print(
            f"{result.prompt_reference} provider={result.provider} "
            f"offline={str(result.offline).lower()} "
            f"passed={str(result.passed).lower()} - {result.message}"
        )

    if failures:
        print("PROMPT-EVALS: FAILED")
        return 1

    print("PROMPT-EVALS: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["PromptEvalResult", "main", "run_prompt_evaluations"]
