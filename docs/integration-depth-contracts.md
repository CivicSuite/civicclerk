# CivicClerk Integration Depth Contracts

CivicClerk v1.0.1 proves its external integration depth with no-network,
adversarial mock contracts. These contracts let the product finish its side of
the Unified Spec integrations before CivicRecords, CivicCode, city CMS adapters,
codification adapters, or live agenda-vendor tenants are available.

Release proof remains adversarial mock validation. No external deployment proof
is required for release.

## CivicRecords Search Bridge

Status: live emitter available when configured; local queue remains available
when CivicCode is absent or unreachable.

Supported operations:

- permission-aware meeting archive query
- closed-session refusal parity
- source citation round-trip
- unavailable-service fallback

If CivicRecords is absent, CivicClerk keeps local public archive search
authoritative and returns an actionable unavailable-state contract instead of
implying CivicRecords is live. Closed-session expansion remains role-gated.

Operator path: configure the CivicRecords base URL and token in deployment
secrets, run the adversarial mock search suite, then enable cross-module search.

## CivicCode Adopted-Action Handoff

Status: ready by contract and mock.

Supported operations:

- ordinance/resolution payload export to CivicCode
- legal reviewer and motion provenance
- idempotency key generation
- retry/audit ledger shape

If CivicCode is absent, CivicClerk stores handoffs locally as
`READY_FOR_CODE_OR_LEGAL_REVIEW` and keeps a file-export path available until
CivicCode is reachable.

Operator path: configure `CIVICCODE_INTAKE_URL` and the matching
`CIVICCODE_INTAKE_SECRET` value that CivicCode expects. New
ordinance/resolution handoffs emit immediately to the configured CivicCode
intake endpoint. Failed or unconfigured handoffs remain visible on the local
record as `EMIT_FAILED` or `EMIT_SKIPPED_UNCONFIGURED`; operators can retry
with `POST /meetings/{meeting_id}/ordinance-resolution-handoff/retry`.

## Codification-System Fallback Export

Status: ready by file contract and mock.

Supported operations:

- records-ready JSON export
- checksum manifest
- source packet references
- human codifier review gate

If CivicCode or a codifier API is absent, CivicClerk produces a checksumed
handoff packet for clerk, legal, and codifier review. It does not auto-codify
or produce legal advice.

Operator path: give the export bundle to the codifier or configure the future
adapter, then record the external codification reference on the adopted item.

## City Website CMS Posting

Status: ready by preview contract and mock.

Supported operations:

- posting preview
- clerk confirmation gate
- withdrawal/rollback ledger shape
- CMS unavailable fallback

If a city CMS adapter is absent, CivicClerk continues to serve the resident
portal and produces a CMS-ready posting preview. Publication is blocked until a
clerk confirms the preview.

Operator path: select the city CMS adapter, store credentials outside the app,
run the mock publish/withdrawal suite, then let the clerk confirm each posting.

## Vendor Live API Adapters

Status: ready by guarded adapter contracts.

Supported operations:

- Granicus delta contract
- Legistar delta contract
- PrimeGov delta contract
- NovusAGENDA delta contract
- circuit breaker and cursor controls

CivicClerk records source configuration, health, cursor resets, and run
outcomes without pulling vendor networks until a controlled adapter run is
explicitly enabled. The hostile mock suite covers rate limits, pagination,
schema drift, partial outage, duplicate IDs, and stale deltas.

Operator path: use local export-drop ingestion until IT approves a source URL,
credentials are stored in deployment secrets, and the no-network hostile vendor
suite passes.

## Runtime Evidence

The admin endpoint `GET /integrations/readiness` returns:

- `network_calls=false`
- `dependent_modules_required=false`
- the five contracts above
- adversarial check results for CivicRecords, CivicCode, codification export,
  CMS posting, and vendor live API adapters

The React admin settings page displays these contracts so IT and clerk admins
can see what is mock-proven, what remains dependency-bound, and exactly what to
do before enabling a real integration.
