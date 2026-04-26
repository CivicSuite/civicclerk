# CivicClerk ADR-0001: Canonical v0.1.0 Table List

Status: Proposed

## Context

AGENTS.md §6 lists fourteen canonical CivicClerk tables. Existing scaffold documentation describes an MVP-sized table subset and omits several canonical tables, including `staff_reports`, `public_comments`, `notices`, `minutes`, `transcripts`, `action_items`, `ordinances_adopted`, and `closed_sessions`.

## Decision

Status: Open Question - pending human decision.

## Consequences

- If v0.1.0 keeps all fourteen canonical tables, Milestone 2 must create and test the full schema.
- If v0.1.0 reduces the table list, the reduction must be explicitly documented and tested.
- Any deviation from AGENTS.md §6 requires this ADR to move from Proposed to Accepted before schema work starts.
