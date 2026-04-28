# Production Depth - Agenda Item Persistence

Date: 2026-04-28
Branch: `feature-depth/agenda-item-persistence`

## Scope

This slice closes the remaining agenda-item runtime gap by making agenda item
lifecycle records durable when `CIVICCLERK_AGENDA_ITEM_DB_URL` is configured.
The existing in-memory behavior remains the default for lightweight local smoke
checks.

## What Shipped

- `AgendaItemRepository` persists agenda item lifecycle status and audit entries
  with SQLAlchemy.
- `/agenda-items`, `/agenda-items/{id}`, `/agenda-items/{id}/transitions`, and
  `/agenda-items/{id}/audit` use the configured repository when
  `CIVICCLERK_AGENDA_ITEM_DB_URL` is set.
- Alembic migration `civicclerk_0006_agenda_items` adds
  `civicclerk.agenda_item_lifecycle_records`.
- Regression tests prove status/audit persistence through both the repository
  and API runtime paths.
- README, README.txt, USER-MANUAL.md, USER-MANUAL.txt, CHANGELOG, and landing
  page copy now describe the shipped persistence path honestly.
- Browser QA evidence confirms the landing page renders the new persistence copy
  on desktop and mobile with zero console errors.

## Verification

```bash
python -m pytest --collect-only -q
# 385 tests collected

python -m pytest -q
# 385 passed

bash scripts/verify-docs.sh
# VERIFY-DOCS: PASSED

python scripts/check-civiccore-placeholder-imports.py
# PLACEHOLDER-IMPORT-CHECK: PASSED

python scripts/verify-browser-qa.py
# BROWSER-QA: PASSED

python -m ruff check civicclerk tests
# All checks passed!

CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py
# PROMPT-EVALS: PASSED

bash scripts/verify-release.sh
# VERIFY-RELEASE: PASSED
```

## Browser QA Evidence

- `docs/browser-qa-production-depth-agenda-item-persistence-desktop.png`
- `docs/browser-qa-production-depth-agenda-item-persistence-mobile.png`
- `docs/browser-qa-production-depth-agenda-item-persistence-summary.md`

## Out of Scope

- Full multi-role React console.
- Installer packaging.
- Public portal expansion.
- New agenda intake workflow behavior beyond the existing staff/API slice.
