# ADR-0001: CivicClerk MVP Boundary

Status: Accepted  
Date: 2026-04-26

## Decision

CivicClerk starts with meeting administration: meeting bodies, meetings,
agenda intake, packet assembly, notice tracking, motions/votes, minutes,
and public meeting archives.

It does not start with livestream hosting, electronic voting, full
transcription packaging, CivicCode integration, or broad boards and
commissions management.

## Rationale

The legal record of meetings is high-value, clerk-owned, and close to
the existing CivicRecords AI architecture. A narrow vertical slice gives
the team something usable and auditable before expanding into adjacent
modules.

## Consequences

- First runtime work must prioritize clerk UX over breadth.
- Public pages ship only after staff posting workflows are safe.
- AI drafting must show citations and require human approval.
