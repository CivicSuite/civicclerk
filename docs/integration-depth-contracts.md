# CivicMeetings Integration Depth Contracts

CivicMeetings reports integration depth as live-wire or in-process boundary
validation. Adversarial mock checks remain useful regression coverage, but they
are not labeled as release-depth proof for CivicRecords, CivicCode, city CMS
adapters, codification adapters, or live agenda-vendor tenants.

## CivicRecords Search Bridge

Status: live-wire boundary required; local archive search remains available
when CivicRecords is absent or unreachable.

Supported operations:

- permission-aware meeting archive query
- closed-session refusal parity
- source citation round-trip
- unavailable-service fallback

If CivicRecords is absent, CivicMeetings keeps local public archive search
authoritative and returns an actionable unavailable-state contract instead of
implying CivicRecords is live. Closed-session expansion remains role-gated.

Operator path: configure the CivicRecords base URL and token in deployment
settings, validate the live or in-process boundary, then keep adversarial search
checks as regression coverage.

## CivicCode Adopted-Action Handoff

Status: live-wire boundary available when configured.

Supported operations:

- ordinance/resolution payload export to CivicCode
- legal reviewer and motion provenance
- idempotency key generation
- retry/audit ledger shape

If CivicCode is absent, CivicMeetings stores handoffs locally as
`READY_FOR_CODE_OR_LEGAL_REVIEW` and keeps a file-export path available until
CivicCode is reachable.

Operator path: configure `CIVICCODE_INTAKE_URL` and the suite bearer value
CivicCode expects. New ordinance/resolution handoffs emit immediately to the
configured CivicCode intake endpoint with `Authorization: Bearer ...` and
`X-CivicSuite-Session-Actor` audit context. Failed or unconfigured handoffs
remain visible on the local record as `EMIT_FAILED` or
`EMIT_SKIPPED_UNCONFIGURED`; operators can retry with
`POST /meetings/{meeting_id}/ordinance-resolution-handoff/retry`.

## Codification-System Fallback Export

Status: in-process boundary validation.

Supported operations:

- records-ready JSON export
- checksum manifest
- source packet references
- human codifier review gate

If CivicCode or a codifier API is absent, CivicMeetings produces a checksumed
handoff packet for clerk, legal, and codifier review. It does not auto-codify
or produce legal advice.

Operator path: give the export bundle to the codifier or configure the future
adapter, then record the external codification reference on the adopted item.

## City Website CMS Posting

Status: live-wire boundary required before CMS posting is claimed.

Supported operations:

- posting preview
- clerk confirmation gate
- withdrawal/rollback ledger shape
- CMS unavailable fallback

If a city CMS adapter is absent, CivicMeetings continues to serve the resident
portal and produces a CMS-ready posting preview. Publication is blocked until a
clerk confirms the preview.

Operator path: select the city CMS adapter, store credentials outside the app,
validate the live posting/withdrawal boundary, then let the clerk confirm each
posting.

## Vendor Live API Adapters

Status: live-wire boundary required for enabled vendor adapters.

Supported operations:

- Granicus delta contract
- Legistar delta contract
- PrimeGov delta contract
- NovusAGENDA delta contract
- circuit breaker and cursor controls

CivicMeetings records source configuration, health, cursor resets, and run
outcomes without pulling vendor networks until a controlled adapter run is
explicitly enabled. The hostile mock suite remains regression coverage for rate
limits, pagination, schema drift, partial outage, duplicate IDs, and stale
deltas.

Operator path: use local export-drop ingestion until IT approves a source URL,
credentials are stored in deployment secrets, and the no-network hostile vendor
suite passes.

## Runtime Evidence

The admin endpoint `GET /integrations/readiness` returns:

- `proof_model=live_or_in_process_boundary_validation`
- `network_calls=true`
- `dependent_modules_required=true`
- the five contracts above
- supplemental adversarial check results for CivicRecords, CivicCode,
  codification export, CMS posting, and vendor live API adapters

The React admin settings page displays these contracts so IT and clerk admins
can see which boundaries require live or in-process validation, what remains
dependency-bound, and exactly what to do before enabling a real integration.
