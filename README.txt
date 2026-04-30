# CivicClerk

**CivicClerk is the CivicSuite module for municipal meetings, agendas, packets, minutes, votes, notices, and public meeting archives.**

Status: CivicClerk v0.1.11 runtime foundation release
Current version: `0.1.11`
Repository: <https://github.com/CivicSuite/civicclerk>
Depends on: published `civiccore` v0.16.0 release wheel

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

CivicClerk v0.1.11 ships the runtime and schema foundation plus database-backed agenda item lifecycle records, meeting lifecycle, packet snapshot, shared CivicCore-backed notice compliance, immutable motion capture, immutable vote capture, action-item capture, citation-gated minutes draft capture, permission-aware public calendar/detail/archive endpoints, a prompt YAML library with an offline evaluation harness, local-first connector imports for Granicus, Legistar, PrimeGov, and NovusAGENDA, accessibility/browser QA gates, CivicCore v0.16.0-backed records export bundles, database-backed agenda intake readiness, database-backed packet assembly records, database-backed notice checklist/posting-proof records, database-backed meeting records, and first staff workflow screens for intake, packet assembly/export, notice checklist, meeting outcome, minutes draft, public archive, and connector import work. The staff screens now submit agenda intake, record readiness review, create/finalize packet assembly records, create records-ready packet export bundles, persist notice checklist records, attach posting proof, capture motions/votes/action items, create citation-gated minutes drafts, publish public-safe archive records, normalize local connector exports through the shared CivicCore connector import contract, consume the shared CivicCore trusted-header config and proxy-source enforcement helpers, and expose `/staff/auth-readiness` so operators can verify whether bearer or trusted-header staff auth is deployment-ready before testing a live session. When bearer or trusted-header mode is ready, the readiness contract now includes a concrete protected-session probe and a protected-write probe instead of only env-var reminders, and trusted-header readiness now carries a loopback-only local proxy rehearsal contract that points operators to `scripts/local_trusted_header_proxy.py` with `127.0.0.1/32` as the safe starter allowlist.

Shipped in this foundation:

- project README
- user manual with non-technical, IT/technical, and architecture sections
- GitHub Pages landing page at `docs/index.html`
- contributing, support, security, code of conduct, issue templates, and PR template
- discussion seed posts
- docs verification script and CI workflow
- Python package metadata with the published `civiccore` v0.16.0 release wheel
- FastAPI application import path at `civicclerk.main:app`
- root endpoint that explains the current product state
- `/health` endpoint for IT staff
- `/staff` staff workflow screens for agenda intake, packet assembly/export, notice checklist/posting-proof, meeting outcome, minutes draft, public archive, and connector import work
- live `/staff` agenda intake submission and clerk readiness-review form actions backed by `/agenda-intake`
- live `/staff` packet assembly create/finalize form actions backed by `/meetings/{id}/packet-assemblies`
- live `/staff` packet export form actions backed by `/meetings/{id}/packet-snapshots` and `/meetings/{id}/export-bundle`
- live `/staff` notice checklist and posting-proof form actions backed by `/meetings/{id}/notice-checklists`
- database-backed agenda intake queue with clerk readiness review state and
  Alembic migration `civicclerk_0002_intake_queue`
- `/agenda-intake` submit/list/review endpoints with audit events for consequential review actions
- canonical SQLAlchemy metadata for the fourteen CivicClerk tables
- Alembic scaffold and first idempotent migration for the `civicclerk` schema
- agenda item lifecycle enforcement from `DRAFTED` through `ARCHIVED`
- optional database-backed agenda item lifecycle persistence with `CIVICCLERK_AGENDA_ITEM_DB_URL`
- audit entries for allowed and rejected agenda item transitions
- meeting lifecycle enforcement from `SCHEDULED` through `ARCHIVED`
- database-backed meeting records with lifecycle audit entries, scheduled
  starts, normalized meeting type, and Alembic migration
  `civicclerk_0005_meetings`
- emergency/special meeting notice preconditions requiring a statutory basis
- closed/executive session in-progress preconditions requiring a statutory basis
- cancellation support from scheduled or noticed meetings, with terminal-state audit entries
- packet snapshot versioning for meetings
- database-backed packet assembly records with source references, citations,
  packet snapshot linkage, and Alembic migration `civicclerk_0003_packet_asm`
- `/meetings/{id}/packet-assemblies` create/list endpoint and
  `/packet-assemblies/{id}/finalize` endpoint with durable audit hashes
- notice compliance checks for deadlines, statutory basis, and human approval
- database-backed notice checklist and posting-proof records with Alembic
  migration `civicclerk_0004_notice_ck`
- `/meetings/{id}/notice-checklists` create/list endpoint and
  `/notice-checklists/{id}/posting-proof` endpoint with durable audit hashes
- approved public notice posting records with actionable warning/error responses
- immutable captured motions with append-only correction records
- immutable captured votes with append-only correction records
- action items linked to meeting outcomes and source motions
- live `/staff` meeting outcome form actions backed by `/meetings/{id}/motions`,
  `/motions/{id}/votes`, and `/meetings/{id}/action-items`
- live `/staff` minutes draft form actions backed by
  `/meetings/{id}/minutes/drafts`
- live `/staff` public archive form actions backed by
  `/meetings/{id}/public-record`, `/public/meetings`, and
  `/public/archive/search`
- live `/staff` connector import form actions backed by
  `/imports/{connector}/meetings`
- citation-gated minutes draft records
- provenance for minutes drafts: model, prompt version, data sources, and human approver
- rejection of uncited AI-drafted minutes output before it can be accepted
- permission-aware public meeting calendar, detail, and archive search endpoints
- first resident-facing public portal shell at `/public` over the public calendar,
  detail, and archive search APIs
- closed-session leak prevention for anonymous public archive bodies, counts, suggestions, and not-found responses
- YAML prompt library under `prompts/`
- offline prompt evaluation harness that runs with `CIVICCORE_LLM_PROVIDER=ollama` and outbound network blocked
- prompt-version provenance enforcement for minutes drafts
- local-first Granicus, Legistar, PrimeGov, and NovusAGENDA meeting imports
- source provenance on imported meetings and agenda items
- records-ready packet export bundles with CivicCore v0.16.0 manifests, SHA256 checksums, provenance, and hash-chained audit events
- closed-session/restricted source guardrails for public packet export bundles
- safe API export-path handling through `bundle_name` under `CIVICCLERK_EXPORT_ROOT`
- browser QA gate covering loading, success, empty, error, and partial states
- accessibility checks for keyboard navigation, focus states, contrast, and console errors
- CivicClerk v0.1.11 release gate and build artifacts
- `scripts/start_fresh_install_rehearsal.ps1` to rehearse the documented
  Windows-first wheel install and first-run smoke checks from an isolated
  `.fresh-install-rehearsal` virtual environment
- `scripts/start_fresh_install_rehearsal.sh` to rehearse the same fresh-install
  wheel path from Bash on Linux, macOS, or Git Bash
- `scripts/build_release_handoff_bundle.ps1` to package the built wheel, sdist,
  checksums, current docs, proxy reference, and rehearsal helpers into a
  repeatable IT handoff zip without calling it an installer
- `/staff/session` to report whether the live staff shell is in local open mode, bearer-protected staff mode, or trusted-header staff mode
- `/staff/auth-readiness` to report whether the current bearer-token or trusted-header staff auth contract is deployment-ready
- structured `session_probe` and `write_probe` guidance from `/staff/auth-readiness` when bearer or trusted-header deployment is ready
- structured `reverse_proxy_reference` guidance from `/staff/auth-readiness` when trusted-header deployment needs a real nginx bridge starting point
- structured `local_proxy_rehearsal` guidance from `/staff/auth-readiness` when trusted-header mode needs a safe loopback-only rehearsal path
- `CIVICCLERK_STAFF_AUTH_MODE=open|bearer|trusted_header` for the first staff auth foundation contract
- `CIVICCLERK_STAFF_AUTH_TOKEN_ROLES` for bearer-token-to-role mapping during staff workflow access
- `CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER`, `CIVICCLERK_STAFF_SSO_ROLES_HEADER`, `CIVICCLERK_STAFF_SSO_PROVIDER`, and `CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES` for trusted reverse-proxy SSO bridge configuration

Not shipped yet:

- full frontend app
- installer
- finished public portal beyond the first `/public` HTML shell
- the integrated multi-role React clerk console beyond this HTML staff workflow surface

## New user experience today

A new user can inspect and run the foundation, open first staff workflow screens at `/staff`, open the first resident-facing public portal shell at `/public`, submit agenda intake items into a database-backed queue from the browser, record clerk readiness review from the browser, create/finalize packet assembly records from the browser, persist notice checklist/posting-proof records from the browser, capture motions/votes/action items from the browser, create citation-gated minutes drafts from the browser, publish public-safe archive records from the browser, normalize local connector exports from the browser, persist agenda item lifecycle records through `CIVICCLERK_AGENDA_ITEM_DB_URL`, persist meeting records and lifecycle audit entries through `CIVICCLERK_MEETING_DB_URL`, create draft agenda items and meetings through the API, and generate a records-ready packet export bundle with manifest, checksums, provenance, and audit evidence. They cannot use CivicClerk for end-to-end meeting work yet. The correct next experience is:

1. Read this README.
2. Read `USER-MANUAL.md`.
3. Read `docs/roadmap/mvp-plan.md`.
4. On Windows PowerShell, create a fresh virtual environment and install the current wheel:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install dist/civicclerk-0.1.11-py3-none-any.whl
   ```

5. Start the FastAPI app from the installed package:

   ```powershell
   $env:CIVICCLERK_STAFF_AUTH_MODE="open"
   python -m uvicorn civicclerk.main:app --host 127.0.0.1 --port 8776
   ```

6. Confirm the fresh-machine smoke-check path:
   - `GET http://127.0.0.1:8776/health` must return `{"status":"ok","service":"civicclerk","version":"0.1.11","civiccore":"0.16.0"}`
   - `GET http://127.0.0.1:8776/staff/auth-readiness` must report `mode: "open"` and explain how to switch to bearer or trusted-header deployment
   - Open `http://127.0.0.1:8776/staff` and confirm the first workflow shell loads
   - Open `http://127.0.0.1:8776/public` and confirm the resident public portal shell loads, explains empty public records, and points staff to publish public records from `/staff`
   - Use `powershell -ExecutionPolicy Bypass -File scripts/start_fresh_install_rehearsal.ps1 -PrintOnly` to print the repeatable Windows fresh-install rehearsal plan, or rerun without `-PrintOnly` to create `.fresh-install-rehearsal\.venv`, install the release wheel, start the installed app, and run the same smoke checks automatically
   - Use `bash scripts/start_fresh_install_rehearsal.sh --print-only` to print the same fresh-install rehearsal plan from Linux, macOS, or Git Bash, or rerun without `--print-only` to create `.fresh-install-rehearsal/.venv`, install the release wheel, start the installed app, and run the same smoke checks automatically; Linux hosts need Python 3 with `venv` support installed first, such as `python3-venv` on Debian or Ubuntu
   - Use `powershell -ExecutionPolicy Bypass -File scripts/build_release_handoff_bundle.ps1 -PrintOnly` to preview the release handoff bundle, or rerun without `-PrintOnly` after `bash scripts/verify-release.sh` has built `dist/` artifacts
   - Use `powershell -ExecutionPolicy Bypass -File scripts/start_protected_demo_rehearsal.ps1 -PrintOnly` on Windows PowerShell or `bash scripts/start_protected_demo_rehearsal.sh --print-only` on Linux, macOS, or Git Bash to print the protected trusted-header demo profile before launching it
7. Exercise `/agenda-intake`, `/agenda-intake/{id}/review`, `/agenda-items`, `/agenda-items/{id}/transitions`, `/meetings`, `/meetings/{id}/transitions`, `/meetings/{id}/packet-snapshots`, `/meetings/{id}/packet-assemblies`, `/packet-assemblies/{id}/finalize`, `/meetings/{id}/notice-checklists`, `/notice-checklists/{id}/posting-proof`, `/meetings/{id}/export-bundle`, `/meetings/{id}/notices/post`, `/meetings/{id}/motions`, `/motions/{id}/votes`, `/meetings/{id}/action-items`, `/meetings/{id}/minutes/drafts`, `/meetings/{id}/public-record`, `/public/meetings`, `/public/archive/search`, and `/imports/{connector}/meetings` to smoke-check Milestone 10 plus the production-depth live staff action slices.
8. Set `CIVICCLERK_AGENDA_ITEM_DB_URL` before agenda item lifecycle persistence smoke checks, set `CIVICCLERK_MEETING_DB_URL` before meeting persistence smoke checks, and set `CIVICCLERK_EXPORT_ROOT` before API packet export smoke checks; API callers provide a relative `bundle_name`, not an arbitrary filesystem path.
9. In bearer or trusted-header mode, call `/staff/auth-readiness` first and use the returned `session_probe` plus `write_probe` before trusting a protected deployment.
10. If trusted-header mode is headed toward a real deployment, start from the returned `reverse_proxy_reference` block and the shipped `docs/examples/trusted-header-nginx.conf` sample before you wire in your real identity provider variables and TLS paths.
11. If trusted-header mode is still being rehearsed on one workstation, use the returned `local_proxy_rehearsal` block, set `CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES=127.0.0.1/32`, run `python scripts/local_trusted_header_proxy.py`, and browse the helper listen URL instead of the upstream app URL.
12. If you want the trusted-header demo profile without hand-exporting env vars on Windows PowerShell, run `powershell -ExecutionPolicy Bypass -File scripts/start_protected_demo_rehearsal.ps1 -PrintOnly` to print the exact commands, then rerun the same script without `-PrintOnly` to launch the app on `8877` and the helper proxy on `8878`.
13. If you want the same protected demo profile from Bash on Linux, macOS, or Git Bash, run `bash scripts/start_protected_demo_rehearsal.sh --print-only` first, then rerun without `--print-only` to launch the app on `8877` and the helper proxy on `8878`.
14. Run `CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py` before changing prompt YAML.
15. Run `python scripts/verify-browser-qa.py` before landing frontend or browser-visible documentation changes.
16. Follow GitHub issues and discussions as live sync, full UI, and database-backed workflows land.

## Architecture direction

CivicClerk follows the CivicSuite pattern:

- FastAPI backend
- React frontend
- PostgreSQL 17 + pgvector
- Redis 7.2 + Celery + Celery Beat
- Ollama / Gemma 4 through `civiccore.llm`, selected by `CIVICCORE_LLM_PROVIDER=ollama`
- local data ownership, no runtime telemetry, no cloud inference

The foundation is intentionally thin. Canonical schema, Alembic scaffolding, agenda item lifecycle enforcement, agenda item lifecycle persistence, meeting lifecycle enforcement, meeting records, packet snapshot versioning, packet assembly records, notice checklist records, shared notice compliance enforcement, immutable motion capture, immutable vote capture, action-item capture, citation-gated minutes draft capture, permission-aware public archive endpoints, prompt YAML/evaluation gates, local-first connector import normalization, browser QA gates, CivicClerk v0.1.11 release artifacts, and CivicCore v0.16.0 packet export plus browser-evidence verification and trusted-header config primitives are present. Minutes drafts require sentence-level citations, YAML prompt-version provenance, and human approval before acceptance, and they are never auto-adopted or auto-posted. Anonymous public archive endpoints do not reveal closed-session content in response bodies, counts, suggestions, or error messages. Connector imports record source provenance and do not require outbound network calls in the default local profile. Public packet exports block closed-session/restricted sources and include manifest, checksum, provenance, and audit evidence. Agenda item records now persist lifecycle status and audit entries when `CIVICCLERK_AGENDA_ITEM_DB_URL` is configured. Meeting records now persist scheduled starts, normalized meeting type, lifecycle status, and audit entries when `CIVICCLERK_MEETING_DB_URL` is configured. Packet assembly records now persist source references, citations, linked packet snapshot ids, and durable audit hashes. Notice checklist records persist compliance outcomes, warnings, posting proof, and durable audit hashes. Browser QA now checks loading, success, empty, error, and partial states plus keyboard, focus, contrast, and console evidence, and release screenshots are bound to the current docs page through shared CivicCore verification helpers. CivicClerk v0.1.11 now pairs with the published `civiccore` v0.16.0 release wheel. The first staff auth foundation is now explicit: local rehearsals can stay in `CIVICCLERK_STAFF_AUTH_MODE=open`, bearer-protected deployments can set `CIVICCLERK_STAFF_AUTH_MODE=bearer` plus `CIVICCLERK_STAFF_AUTH_TOKEN_ROLES`, and trusted reverse-proxy deployments can set `CIVICCLERK_STAFF_AUTH_MODE=trusted_header` plus `CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER`, `CIVICCLERK_STAFF_SSO_ROLES_HEADER`, `CIVICCLERK_STAFF_SSO_PROVIDER`, and `CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES` until full OIDC login lands. The `/staff/auth-readiness` endpoint now tells operators whether those bearer or trusted-proxy settings are merely present or actually deployment-ready, and it includes a loopback-only rehearsal recipe so trusted-header testing does not require inventing a custom proxy first.

The staff experience at `/staff` now includes first workflow screens for agenda intake, packet assembly/export, notice checklist/posting-proof, meeting outcome, minutes draft, public archive, and connector import work. It is intentionally honest: these seven screens can submit their corresponding live API actions, the auth panel now renders concrete protected-session and protected-write probes from `/staff/auth-readiness` when bearer or trusted-header mode is ready, it surfaces the loopback-only local proxy rehearsal command and env vars when trusted-header mode is being staged, and the broader multi-role React clerk console remains future work. The resident-facing `/public` shell now gives the same honesty on the public side: it loads public calendar records, public-safe detail, and anonymous archive search from the live public APIs, shows actionable loading/empty/error states, and says the finished public portal is still future work.

For the first real trusted-header deployment handoff, `docs/examples/trusted-header-nginx.conf` now ships a reference nginx bridge that strips client-supplied identity headers, sets proxy-owned staff headers, and points operators back to `CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES` plus the `/staff/auth-readiness` contract before live staff traffic is trusted.

For fresh Windows install rehearsals, `scripts/start_fresh_install_rehearsal.ps1` now prints and can execute the documented wheel-install path from an isolated `.fresh-install-rehearsal` virtual environment: create venv, upgrade pip, install `dist/civicclerk-0.1.11-py3-none-any.whl`, set `CIVICCLERK_STAFF_AUTH_MODE=open`, launch the installed app on `127.0.0.1:8776`, verify `/health`, verify `/staff/auth-readiness`, and fetch `/staff`. If the wheel is missing, the helper tells the operator to build it with `python -m build` before trying again.

For fresh Bash install rehearsals on Linux, macOS, or Git Bash, `scripts/start_fresh_install_rehearsal.sh` now prints and can execute the same wheel-install path from an isolated `.fresh-install-rehearsal/.venv`, with the same `/health`, `/staff/auth-readiness`, `/staff`, missing-wheel, occupied-port, and Python `venv` prerequisite checks as the Windows helper. On Debian or Ubuntu, install `python3-venv` before executing the helper.

For IT release handoff, `scripts/build_release_handoff_bundle.ps1` now prints and can create `dist/civicclerk-0.1.11-release-handoff.zip` containing the built wheel, source distribution, checksums, current README/manual/changelog/license, docs landing page, trusted-header nginx reference, and the fresh-install/protected-demo rehearsal helpers. It intentionally refuses to overwrite an existing bundle and it is not an installer; build artifacts first with `bash scripts/verify-release.sh`.

For protected demos on Windows PowerShell, `scripts/start_protected_demo_rehearsal.ps1` now prints and can launch the loopback-only trusted-header profile end to end: the app on `127.0.0.1:8877`, the helper proxy on `127.0.0.1:8878`, the required trusted-header env vars, the health/readiness checks, and the browser target for `/staff`.

For Bash-based operator rehearsals on Linux, macOS, or Git Bash, `scripts/start_protected_demo_rehearsal.sh` now prints and can launch the same loopback-only trusted-header profile with `export` commands and the same smoke-check/browser targets instead of leaving Unix shell parity undocumented.

## Verification

Before every push:

```bash
python -m pytest
bash scripts/verify-docs.sh
python scripts/check-civiccore-placeholder-imports.py
python scripts/verify-browser-qa.py
CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py
bash scripts/verify-release.sh
```

## License

Code: Apache License 2.0; see `LICENSE-CODE`.  
Documentation: CC BY 4.0 unless otherwise stated; see `LICENSE-DOCS`.
