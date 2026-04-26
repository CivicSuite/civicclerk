# CivicClerk ADR-0003: Transcription Packaging Scope

Status: Proposed

## Context

The existing CivicClerk scaffold ADR excludes "full transcription packaging" from the MVP, while AGENTS.md §6 lists `civicclerk.transcripts` as a canonical table and AGENTS.md §5 includes minutes drafting with cited source material.

## Decision

Status: Open Question - pending human decision.

## Consequences

- If transcripts ship in v0.1.0, Milestones 2, 7, and 8 need schema, citation, permission, and public archive coverage.
- If transcripts are deferred to v0.2.0, minutes drafting still needs source-citation behavior without overstating transcription capability.
- The current accepted scaffold ADR must be superseded or amended before implementation.
