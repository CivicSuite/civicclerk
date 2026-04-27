"""Versioned prompt library loaded from repository YAML files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from string import Template


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


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
    required_variables: tuple[str, ...]
    template: str
    evaluations: tuple[PromptEvaluation, ...]

    @property
    def reference(self) -> str:
        return f"{self.id}@{self.version}"


def load_prompt(prompt_id: str) -> PromptDefinition:
    """Load a prompt definition by id from the local prompt YAML directory."""
    prompt_path = PROMPTS_DIR / f"{prompt_id}.yaml"
    if not prompt_path.exists():
        raise PromptLibraryError(
            f"Prompt '{prompt_id}' is not present in the CivicClerk YAML prompt library."
        )
    return _parse_prompt_yaml(prompt_path.read_text(encoding="utf-8"))


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
    """Parse the limited YAML shape used by CivicClerk prompt files."""
    lines = raw.splitlines()
    scalar_values: dict[str, str] = {}
    required_variables: list[str] = []
    evaluations: list[PromptEvaluation] = []
    template_lines: list[str] = []
    mode: str | None = None
    current_eval_name: str | None = None
    current_eval_phrases: list[str] = []

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
            if mode == "template":
                template_lines.append("")
            continue

        if mode == "template":
            if line.startswith("  "):
                template_lines.append(line[2:])
                continue
            mode = None

        if stripped in {"required_variables:", "evaluations:"}:
            mode = stripped[:-1]
            if mode == "evaluations":
                flush_eval()
            continue

        if stripped == "template: |":
            mode = "template"
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

    flush_eval()

    required_keys = {"id", "version", "provider"}
    missing_keys = sorted(required_keys - scalar_values.keys())
    if missing_keys:
        raise PromptLibraryError(
            "Prompt YAML is missing required keys: " + ", ".join(missing_keys)
        )
    if not required_variables:
        raise PromptLibraryError("Prompt YAML must declare required_variables.")
    if not template_lines:
        raise PromptLibraryError("Prompt YAML must include a template block.")

    return PromptDefinition(
        id=scalar_values["id"],
        version=scalar_values["version"],
        provider=scalar_values["provider"],
        required_variables=tuple(required_variables),
        template="\n".join(template_lines).strip(),
        evaluations=tuple(evaluations),
    )


__all__ = [
    "PROMPTS_DIR",
    "PromptDefinition",
    "PromptEvaluation",
    "PromptLibraryError",
    "expected_prompt_version_hint",
    "is_known_prompt_version",
    "load_prompt",
    "render_prompt",
]
