# CivicClerk

**CivicClerk is the CivicSuite module for municipal meetings, agendas, packets, minutes, votes, notices, and public meeting archives.**

Status: runtime foundation  
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

This repository now ships the CivicClerk runtime foundation. Meeting workflows are not implemented yet.

Shipped in this runtime foundation:

- project README and plain-text README
- user manual with non-technical, IT/technical, and architecture sections
- GitHub Pages landing page at `docs/index.html`
- contributing, support, security, code of conduct, issue templates, and PR template
- discussion seed posts
- docs verification script and CI workflow
- Python package metadata with `civiccore==0.2.0`
- FastAPI application import path at `civicclerk.main:app`
- root endpoint that explains the current product state
- `/health` endpoint for IT staff

Not shipped yet:

- frontend app
- database migrations
- installer
- release artifact
- public portal
- meeting, agenda, packet, notice, vote, minutes, or archive workflows

## New user experience today

A new user can inspect and run the runtime foundation, but cannot use CivicClerk for meeting work yet. The correct next experience is:

1. Read this README.
2. Read `USER-MANUAL.md`.
3. Read `docs/roadmap/mvp-plan.md`.
4. For an IT smoke check, run the FastAPI app at `civicclerk.main:app` and call `/health`.
5. Follow GitHub issues and discussions as meeting workflows land.

## Architecture direction

CivicClerk follows the CivicSuite pattern:

- FastAPI backend
- React frontend
- PostgreSQL 17 + pgvector
- Redis 7.2 + Celery + Celery Beat
- Ollama / Gemma 4 through `civiccore.llm`, selected by `CIVICCORE_LLM_PROVIDER=ollama`
- local data ownership, no runtime telemetry, no cloud inference

The runtime foundation is intentionally thin. Schema, migrations, lifecycle rules, UI, and AI workflows land in later milestones after their tests.

## Verification

Before every push:

```bash
python -m pytest
bash scripts/verify-docs.sh
python scripts/check-civiccore-placeholder-imports.py
```

## License

Code: Apache License 2.0.  
Documentation: CC BY 4.0 unless otherwise stated.
