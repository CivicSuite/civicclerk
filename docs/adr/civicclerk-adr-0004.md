# CivicClerk ADR-0004: Resident Portal Shell Boundary

Status: Proposed

## Context

CivicClerk needs public meeting calendar, detail, packet, minutes, and archive surfaces. The broader CivicSuite architecture anticipates shared resident-facing portal capabilities, but CivicCore v0.2.0 does not yet ship that shell.

## Decision

Status: Open Question - pending human decision.

## Consequences

- If CivicClerk owns its v0.1.0 public shell, Milestone 8 must include enough UI structure for public pages without claiming suite-wide portal support.
- If a shared shell must exist first, CivicClerk Milestone 8 blocks on upstream CivicCore or umbrella work.
- Documentation must make the shipped/planned boundary clear for residents and municipal staff.
