# CivicClerk

**CivicClerk is the CivicSuite module for municipal meetings, agendas, packets, minutes, votes, notices, and public meeting archives.**

Status: scaffold / planning baseline  
Current version: `0.0.0`  
Repository: <https://github.com/CivicSuite/civicclerk>  
Depends on: `civiccore >=0.2.0, <0.3.0` once runtime work begins

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

This repository is a professional scaffold only. No runtime application has shipped yet.

Shipped in this scaffold:

- project README and plain-text README
- user manual with non-technical, IT/technical, and architecture sections
- GitHub Pages landing page at `docs/index.html`
- contributing, support, security, code of conduct, issue templates, and PR template
- discussion seed posts
- docs verification script and CI workflow

Not shipped yet:

- backend API
- frontend app
- database migrations
- installer
- release artifact
- public portal

## New user experience today

A new user can read the landing page and manuals to understand the intended product, but cannot install CivicClerk yet. The correct next experience is:

1. Read this README.
2. Read `USER-MANUAL.md`.
3. Read `docs/roadmap/mvp-plan.md`.
4. Follow GitHub issues and discussions as the first coded MVP lands.

## Architecture direction

CivicClerk follows the CivicSuite pattern:

- FastAPI backend
- React frontend
- PostgreSQL 17 + pgvector
- Redis + Celery
- Ollama / Gemma 4 through `civiccore.llm`
- local data ownership, no runtime telemetry, no cloud inference

Runtime design details will be locked in ADRs before code lands.

## Verification

Before every push:

```bash
bash scripts/verify-docs.sh
```

## License

Code: Apache License 2.0.  
Documentation: CC BY 4.0 unless otherwise stated.
