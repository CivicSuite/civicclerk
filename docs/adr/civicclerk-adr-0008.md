# CivicClerk ADR-0008: State Statutory Rule Data Strategy

Status: Proposed

## Context

CivicClerk v0.1.0 includes statutory notice deadline tracking and emergency/special meeting statutory-basis capture. The unified spec flags statutory rule data as a suite-level open question.

## Decision

Status: Open Question - pending human decision.

## Consequences

- If statutory rules ship as bundled local data, Milestone 5 must test versioning, update paths, and jurisdiction selection.
- If statutory rules are operator-configured only, UX must make missing or incomplete rule data actionable.
- If statutory rules require a separate shared package, CivicClerk notice compliance may block on upstream CivicCore or umbrella work.
