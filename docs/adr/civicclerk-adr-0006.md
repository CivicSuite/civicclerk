# CivicClerk ADR-0006: Document and Search Extraction Order

Status: Proposed

## Context

AGENTS.md §3.1 marks CivicCore ingest and search packages as placeholders in v0.2.0. CivicClerk v0.1.0 needs packet documents, minutes source material, archive search, and permission-aware public/staff access.

## Decision

Status: Open Question - pending human decision.

## Consequences

- CivicClerk cannot import from `civiccore.ingest` or `civiccore.search` until those packages have real implementations.
- Local document/search behavior must not create a dependency edge from CivicCore back to CivicClerk.
- Archive search tests must cover anonymous users, staff users with insufficient roles, and staff users with permitted roles.
