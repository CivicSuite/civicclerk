"""Versioned prompt library loaded from repository YAML files."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from string import Template

from civiccore.llm import PromptTemplate, register_template_override, resolve_template
from civiccore.db import Base as CivicCoreBase


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
CONSUMER_APP = "civicclerk"
PROMPT_IDS = (
    "agenda_item_summary",
    "staff_report_normalizer",
    "packet_completeness_reviewer",
    "notice_compliance_reviewer",
    "motion_vote_summary",
    "minutes_draft",
    "ordinance_resolution_extractor",
    "closed_session_safe_summarizer",
    "public_plain_language_meeting_explainer",
)


class PromptLibraryError(ValueError):
    """Raised when a prompt cannot be loaded or rendered safely."""


@dataclass(frozen=True)
class PromptEvaluation:
    name: str
    required_phrases: tuple[str, ...]


@dataclass(frozen=True)
class PromptDefinition:
    id: str
    version: str
    provider: str
    purpose: str
    required_variables: tuple[str, ...]
    system_prompt: str
    template: str
    evaluations: tuple[PromptEvaluation, ...]
    public_facing: bool = False
    approval_required: str | None = None

    @property
    def reference(self) -> str:
        return f"{self.id}@{self.version}"

    @property
    def resolver_version(self) -> int:
        parts = [int(part) for part in self.version.split(".")]
        while len(parts) < 3:
            parts.append(0)
        return parts[0] * 10_000 + parts[1] * 100 + parts[2]

    def to_prompt_template(self) -> PromptTemplate:
        return PromptTemplate(
            template_name=self.id,
            consumer_app=CONSUMER_APP,
            is_override=True,
            purpose=self.purpose,
            system_prompt=self.system_prompt,
            user_prompt_template=self.template,
            token_budget={"provider": self.provider, "semantic_version": self.version},
            version=self.resolver_version,
            is_active=True,
        )


def load_prompt(prompt_id: str) -> PromptDefinition:
    """Load a prompt definition by id from the local prompt YAML directory."""
    prompt_path = PROMPTS_DIR / f"{prompt_id}.yaml"
    if not prompt_path.exists():
        raise PromptLibraryError(
            f"Prompt '{prompt_id}' is not present in the CivicMeetings YAML prompt library."
        )
    return _parse_prompt_yaml(prompt_path.read_text(encoding="utf-8"))


def list_prompt_ids() -> tuple[str, ...]:
    return PROMPT_IDS


def list_prompts() -> tuple[PromptDefinition, ...]:
    return tuple(load_prompt(prompt_id) for prompt_id in PROMPT_IDS)


def register_prompt_overrides() -> None:
    for prompt in list_prompts():
        register_template_override(
            consumer_app=CONSUMER_APP,
            template_name=prompt.id,
            template=prompt.to_prompt_template(),
        )
    _remove_civiccore_prompt_tables_from_shared_metadata()


async def resolve_prompt_template(prompt_id: str, *, session=None) -> PromptTemplate:
    register_prompt_overrides()
    return await resolve_template(
        session or _NoDbPromptSession(),
        template_name=prompt_id,
        consumer_app=CONSUMER_APP,
    )


def resolve_prompt_template_sync(prompt_id: str) -> PromptTemplate:
    return asyncio.run(resolve_prompt_template(prompt_id))


def render_prompt(
    prompt: PromptDefinition,
    variables: dict[str, str],
) -> str:
    """Render a prompt template after enforcing all declared variables."""
    missing = [
        variable
        for variable in prompt.required_variables
        if variable not in variables or variables[variable] == ""
    ]
    if missing:
        raise PromptLibraryError(
            "Missing prompt variables: "
            + ", ".join(missing)
            + ". Provide every required variable before rendering."
        )
    return Template(prompt.template).substitute(variables)


def render_prompt_template(
    prompt_template: PromptTemplate,
    variables: dict[str, str],
    required_variables: tuple[str, ...],
) -> str:
    missing = [
        variable
        for variable in required_variables
        if variable not in variables or variables[variable] == ""
    ]
    if missing:
        raise PromptLibraryError(
            "Missing prompt variables: "
            + ", ".join(missing)
            + ". Provide every required variable before rendering."
        )
    return Template(prompt_template.user_prompt_template).substitute(variables)


def is_known_prompt_version(prompt_reference: str) -> bool:
    """Return whether a prompt reference is known by the local YAML library."""
    if "@" not in prompt_reference:
        return False
    prompt_id, version = prompt_reference.split("@", 1)
    try:
        prompt = load_prompt(prompt_id)
    except PromptLibraryError:
        return False
    return prompt.version == version


def expected_prompt_version_hint(prompt_id: str = "minutes_draft") -> str:
    """Return the canonical prompt reference operators should use."""
    return load_prompt(prompt_id).reference


def _parse_prompt_yaml(raw: str) -> PromptDefinition:
    """Parse the limited YAML shape used by CivicMeetings prompt files."""
    lines = raw.splitlines()
    scalar_values: dict[str, str] = {}
    required_variables: list[str] = []
    evaluations: list[PromptEvaluation] = []
    block_values: dict[str, str] = {}
    block_lines: list[str] = []
    block_key: str | None = None
    mode: str | None = None
    current_eval_name: str | None = None
    current_eval_phrases: list[str] = []

    def flush_block() -> None:
        nonlocal block_key, block_lines
        if block_key is not None:
            block_values[block_key] = "\n".join(block_lines).strip()
        block_key = None
        block_lines = []

    def flush_eval() -> None:
        nonlocal current_eval_name, current_eval_phrases
        if current_eval_name is not None:
            evaluations.append(
                PromptEvaluation(
                    name=current_eval_name,
                    required_phrases=tuple(current_eval_phrases),
                )
            )
        current_eval_name = None
        current_eval_phrases = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if block_key is not None:
                block_lines.append("")
            continue

        if block_key is not None:
            if line.startswith("  "):
                block_lines.append(line[2:])
                continue
            flush_block()
            mode = None

        if stripped in {"required_variables:", "evaluations:"}:
            mode = stripped[:-1]
            if mode == "evaluations":
                flush_eval()
            continue

        if stripped in {"system_prompt: |", "template: |"}:
            flush_block()
            block_key = stripped.removesuffix(": |")
            continue

        if mode == "required_variables" and stripped.startswith("- "):
            required_variables.append(stripped[2:])
            continue

        if mode == "evaluations":
            if stripped.startswith("- name: "):
                flush_eval()
                current_eval_name = stripped.removeprefix("- name: ")
                continue
            if stripped == "required_phrases:":
                continue
            if stripped.startswith("- "):
                current_eval_phrases.append(stripped[2:])
                continue

        if ": " in stripped:
            key, value = stripped.split(": ", 1)
            scalar_values[key] = value

    flush_block()
    flush_eval()

    required_keys = {"id", "version", "provider", "purpose"}
    missing_keys = sorted(required_keys - scalar_values.keys())
    if missing_keys:
        raise PromptLibraryError(
            "Prompt YAML is missing required keys: " + ", ".join(missing_keys)
        )
    if not required_variables:
        raise PromptLibraryError("Prompt YAML must declare required_variables.")
    if "system_prompt" not in block_values:
        raise PromptLibraryError("Prompt YAML must include a system_prompt block.")
    if "template" not in block_values:
        raise PromptLibraryError("Prompt YAML must include a template block.")

    return PromptDefinition(
        id=scalar_values["id"],
        version=scalar_values["version"],
        provider=scalar_values["provider"],
        purpose=scalar_values["purpose"],
        required_variables=tuple(required_variables),
        system_prompt=block_values["system_prompt"],
        template=block_values["template"],
        evaluations=tuple(evaluations),
        public_facing=scalar_values.get("public_facing", "false") == "true",
        approval_required=scalar_values.get("approval_required"),
    )


class _NoDbPromptSession:
    async def execute(self, statement):
        return _NoDbPromptResult()


class _NoDbPromptResult:
    def scalar_one_or_none(self):
        return None


def _remove_civiccore_prompt_tables_from_shared_metadata() -> None:
    # CivicMeetings intentionally exposes only the canonical civicclerk schema in
    # shared metadata; the CivicCore resolver ORM tables are owned by CivicCore.
    for table_name in ("prompt_templates", "model_registry"):
        table = CivicCoreBase.metadata.tables.get(table_name)
        if table is not None:
            CivicCoreBase.metadata.remove(table)


register_prompt_overrides()


__all__ = [
    "CONSUMER_APP",
    "PROMPTS_DIR",
    "PROMPT_IDS",
    "PromptDefinition",
    "PromptEvaluation",
    "PromptLibraryError",
    "expected_prompt_version_hint",
    "is_known_prompt_version",
    "list_prompt_ids",
    "list_prompts",
    "load_prompt",
    "register_prompt_overrides",
    "render_prompt",
    "render_prompt_template",
    "resolve_prompt_template",
    "resolve_prompt_template_sync",
]
