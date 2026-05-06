# CivicClerk ADR-0006: Document and Search Extraction Order

Status: Accepted

## Context

CivicClerk needs packet documents, minutes source material, archive search, and
permission-aware public/staff access. CivicCore 1.0.0 ships search helpers but
no document-table package, while `civiccore.ingest`, `civiccore.exports`, and
`civiccore.provenance` cover cited source material and records-ready bundles.

## Decision

CivicClerk uses released CivicCore search helpers for permission-aware archive
search and uses module-local `document_ref` / source-reference fields wherever
canonical tables need to point at packet, minutes, transcript, notice, staff
report, or ordinance material. These references are intentionally opaque until
CivicCore document tables are fully extracted and released.

## Consequences

- `public_archive.py` imports `civiccore.search` instead of carrying a
  module-local search implementation.
- Canonical tables use `document_ref`, `source_references`, or source material
  JSON fields rather than foreign keys to unreleased CivicCore document tables.
- Extraction plan: when CivicCore releases document tables, add an ADR and
  migration that backfills `document_ref` values into shared document foreign
  keys while preserving compatibility tests for existing records.
