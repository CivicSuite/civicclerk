# CivicClerk ADR-0007: Prompt Library Repository Strategy

Status: Proposed

## Context

AGENTS.md requires module-specific YAML prompts under `prompts/`, no hardcoded policy-bearing prompt strings, prompt versioning, provenance capture, and an evaluation harness before prompt changes are released.

## Decision

Status: Open Question - pending human decision.

## Consequences

- If prompts live inside CivicClerk, Milestone 9 must create the prompt tree, CI grep, and evaluation harness in this repo.
- If prompts move to a shared repository later, CivicClerk must still pin versions and preserve provenance.
- Any release with AI behavior must cite prompt version, model, source material, and human approver.
