# Milestone 9 Done: Prompt YAML Library And Evaluation Harness

Status: complete on branch `milestone-9-prompt-yaml-evals`

## Scope Completed

- Prompt policy text for minutes drafting now lives in `prompts/minutes_draft.yaml`.
- Prompt definitions are versioned and loaded through `civicclerk.prompt_library`.
- Prompt rendering enforces declared required variables with actionable errors.
- Minutes drafts must use a prompt reference from the YAML library.
- Minutes provenance records the canonical `minutes_draft@0.1.0` prompt version.
- Offline prompt evaluations run through `scripts/run-prompt-evals.py`.
- CI runs the prompt evaluation harness with `CIVICCORE_LLM_PROVIDER=ollama`, `CIVICCLERK_EVAL_OFFLINE=1`, and `NO_NETWORK=1`.
- The root endpoint, README, user manual, landing page, and changelog now describe the shipped prompt evaluation foundation and point to Milestone 10.

## TDD Evidence

- Red contract commit: `27accb8 test(milestone-9): define prompt yaml eval contract`
- Initial red run: `python -m pytest tests/test_milestone_9_prompt_yaml_evals.py -q`
- Initial result: `6 failed`
- Green implementation commit: `dfddc2b feat(milestone-9): add prompt yaml evaluation gate`
- Targeted green run: `python -m pytest tests/test_milestone_9_prompt_yaml_evals.py tests/test_milestone_7_minutes_citations.py tests/test_milestone_1_runtime_foundation.py -q`
- Targeted result: `22 passed in 0.49s`

## Verification Snapshot

- `python -m pytest --collect-only -q`: `336 tests collected in 0.88s`
- `python -m pytest -q`: `336 passed in 6.46s`
- `bash scripts/verify-docs.sh`: `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py`: `PLACEHOLDER-IMPORT-CHECK: PASSED (16 source files scanned)`
- `python -m ruff check .`: `All checks passed!`
- `CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py`: `PROMPT-EVALS: PASSED`

## Browser QA Evidence

- Desktop landing page QA: `docs/screenshots/milestone9-desktop.png`
- Mobile landing page QA: `docs/screenshots/milestone9-mobile.png`
- Desktop result: Milestone 9 prompt YAML/eval copy visible, stale prompt-planned copy absent, console errors `0`.
- Mobile result: Milestone 9 prompt YAML/eval copy visible, stale prompt-planned copy absent, console errors `0`.

## Runtime Contract

`GET /` now returns:

```json
{
  "name": "CivicClerk",
  "status": "prompt evaluation foundation",
  "message": "CivicClerk agenda item, meeting lifecycle, packet snapshot, and notice compliance enforcement are online with immutable motion, vote, action-item, and citation-gated minutes draft capture plus permission-aware public calendar and archive endpoints; prompt YAML and offline evaluation gates now protect policy-bearing prompt changes; full UI workflows are not implemented yet.",
  "next_step": "Milestone 10: connectors and imports"
}
```

## Out of Scope

- Granicus, Legistar, PrimeGov, and NovusAGENDA connectors/imports.
- Full frontend workflow screens.
- Database-backed prompt/prompt-eval persistence beyond the current runtime slice.
- CivicCore, CivicSuite umbrella, or CivicRecords AI changes.
