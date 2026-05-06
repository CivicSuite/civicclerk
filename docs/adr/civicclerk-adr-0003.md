# CivicClerk ADR-0003: Transcription Packaging Scope

Status: Accepted

## Context

The unified spec lists `civicclerk.transcripts` as a canonical table and the
minutes workflow needs cited source material. Full automatic transcription
packaging is not required for the current product slice, but downstream modules
need a stable place to reference transcript artifacts once a city supplies or
approves them.

## Decision

CivicClerk ships the `transcripts` table as a source-reference index with
`source_uri`, status, optional `document_ref`, sensitivity label, and staff ACL
roles. The table can point at externally produced or later CivicCore-managed
transcript material. CivicClerk does not claim automatic transcription
generation in this release window.

## Consequences

- Minutes drafting can cite transcript source material without inventing a
  separate local table later.
- Staff-only or closed-session transcript material has explicit ACL fields.
- A future transcription package may populate the table, but must preserve the
  existing source-reference contract.
