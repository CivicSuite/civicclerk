# CivicClerk

**CivicClerk is the CivicSuite module for municipal meetings, agendas, packets, minutes, votes, notices, and public meeting archives.**

Status: runtime foundation plus packet/notice compliance enforcement  
Current version: `0.1.0.dev0`  
Repository: <https://github.com/CivicSuite/civicclerk>  
Depends on: `civiccore==0.2.0`

## What CivicClerk will do

CivicClerk is designed for the legal record of public meetings:

- agenda item intake from departments
- packet assembly
- statutory notice deadline tracking
- meeting motions, votes, and action logging
- minute drafting with source citations
- ordinance and resolution adoption-event export
- public meeting pages for posted agendas, packets, and approved minutes
- searchable meeting archives

AI may draft or extract. Humans approve every consequential action.

## What exists today

This repository now ships the CivicClerk runtime and schema foundation plus agenda item lifecycle, meeting lifecycle, packet snapshot, and notice compliance enforcement. Vote, minutes, archive, and full meeting workflow screens are not implemented yet.

Shipped in this foundation:

- project README
- user manual with non-technical, IT/technical, and architecture sections
- GitHub Pages landing page at `docs/index.html`
- contributing, support, security, code of conduct, issue templates, and PR template
- discussion seed posts
- docs verification script and CI workflow
- Python package metadata with `civiccore==0.2.0`
- FastAPI application import path at `civicclerk.main:app`
- root endpoint that explains the current product state
- `/health` endpoint for IT staff
- canonical SQLAlchemy metadata for the fourteen CivicClerk tables
- Alembic scaffold and first idempotent migration for the `civicclerk` schema
- agenda item lifecycle enforcement from `DRAFTED` through `ARCHIVED`
- audit entries for allowed and rejected agenda item transitions
- meeting lifecycle enforcement from `SCHEDULED` through `ARCHIVED`
- emergency/special meeting notice preconditions requiring a statutory basis
- closed/executive session in-progress preconditions requiring a statutory basis
- cancellation support from scheduled or noticed meetings, with terminal-state audit entries
- packet snapshot versioning for meetings
- notice compliance checks for deadlines, statutory basis, and human approval
- approved public notice posting records with actionable warning/error responses

Not shipped yet:

- frontend app
- installer
- release artifact
- public portal
- vote, minutes, or archive workflows
- database-backed agenda item persistence beyond the current runtime slice
- database-backed meeting lifecycle persistence beyond the current runtime slice
- database-backed packet and notice persistence beyond the current runtime slice

## New user experience today

A new user can inspect and run the foundation, create draft agenda items and meetings through the API, version packet snapshots, and test notice compliance checks/posting guardrails. They cannot use CivicClerk for end-to-end meeting work yet. The correct next experience is:

1. Read this README.
2. Read `USER-MANUAL.md`.
3. Read `docs/roadmap/mvp-plan.md`.
4. For an IT smoke check, run the FastAPI app at `civicclerk.main:app` and call `/health`.
5. Exercise `/agenda-items`, `/agenda-items/{id}/transitions`, `/meetings`, `/meetings/{id}/transitions`, `/meetings/{id}/packet-snapshots`, and `/meetings/{id}/notices/post` to smoke-check Milestone 5 behavior.
6. Follow GitHub issues and discussions as vote, minutes, archive, UI, and database-backed workflows land.

## Architecture direction

CivicClerk follows the CivicSuite pattern:

- FastAPI backend
- React frontend
- PostgreSQL 17 + pgvector
- Redis 7.2 + Celery + Celery Beat
- Ollama / Gemma 4 through `civiccore.llm`, selected by `CIVICCORE_LLM_PROVIDER=ollama`
- local data ownership, no runtime telemetry, no cloud inference

The foundation is intentionally thin. Canonical schema, Alembic scaffolding, agenda item lifecycle enforcement, meeting lifecycle enforcement, packet snapshot versioning, and notice compliance enforcement are present; vote capture, minutes, archive, UI, and AI workflows land in later milestones after their tests. The next milestone is motion, vote, and action-item capture.

## Verification

Before every push:

```bash
python -m pytest
bash scripts/verify-docs.sh
python scripts/check-civiccore-placeholder-imports.py
```

## License

Code: Apache License 2.0; see `LICENSE-CODE`.  
Documentation: CC BY 4.0 unless otherwise stated; see `LICENSE-DOCS`.
