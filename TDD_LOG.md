# TDD Log

```json
[
  {
    "milestone": 1,
    "iteration": 1,
    "target_test": "tests/test_milestone_1_runtime_foundation.py::test_pyproject_declares_runtime_package_and_version",
    "tests_passing": 4,
    "tests_failing": 6,
    "files_changed": ["pyproject.toml", "TDD_LOG.md"],
    "commit_sha": "f78217a",
    "notes": "Added pyproject metadata, exact civiccore pin, runtime dependencies, and dev test dependencies."
  },
  {
    "milestone": 1,
    "iteration": 2,
    "target_test": "tests/test_milestone_1_runtime_foundation.py::test_runtime_package_layout_exists",
    "tests_passing": 8,
    "tests_failing": 2,
    "files_changed": ["civicclerk/__init__.py", "civicclerk/main.py", "TDD_LOG.md"],
    "commit_sha": "bbe5648",
    "notes": "Added the minimal FastAPI app import path plus root and health responses."
  },
  {
    "milestone": 1,
    "iteration": 3,
    "target_test": "tests/test_milestone_1_runtime_foundation.py::test_ci_runs_pytest_docs_and_placeholder_gates",
    "tests_passing": 9,
    "tests_failing": 1,
    "files_changed": [".github/workflows/ci.yml", "TDD_LOG.md"],
    "commit_sha": "4f471ab",
    "notes": "Expanded CI from docs-only to install package, run pytest, verify docs, and check placeholder imports."
  },
  {
    "milestone": 1,
    "iteration": 4,
    "target_test": "tests/test_milestone_1_runtime_foundation.py::test_current_facing_docs_describe_runtime_foundation_honestly",
    "tests_passing": 10,
    "tests_failing": 0,
    "files_changed": ["README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "TDD_LOG.md"],
    "commit_sha": "b108b96",
    "notes": "Updated current-facing docs and changelog to describe the shipped runtime foundation without claiming meeting workflows."
  },
  {
    "milestone": 2,
    "iteration": 1,
    "target_test": "tests/test_milestone_2_schema_and_migrations.py::test_canonical_table_models_exist_and_no_tables_are_missing_or_extra",
    "tests_passing": 5,
    "tests_failing": 15,
    "files_changed": ["civicclerk/models.py", "TDD_LOG.md"],
    "commit_sha": "c1eb0a3",
    "notes": "Added canonical SQLAlchemy table metadata for all fourteen CivicClerk tables using CivicCore Base."
  },
  {
    "milestone": 2,
    "iteration": 2,
    "target_test": "tests/test_milestone_2_schema_and_migrations.py::test_alembic_scaffold_exists_for_civicclerk_schema_chain",
    "tests_passing": 19,
    "tests_failing": 1,
    "files_changed": ["civicclerk/migrations/alembic.ini", "civicclerk/migrations/env.py", "civicclerk/migrations/versions/civicclerk_0001_schema.py", "TDD_LOG.md"],
    "commit_sha": "3386c2d",
    "notes": "Added CivicClerk Alembic scaffold and idempotent first migration for the fourteen canonical tables."
  },
  {
    "milestone": 2,
    "iteration": 3,
    "target_test": "tests/test_milestone_2_schema_and_migrations.py::test_docs_and_changelog_record_schema_milestone_without_claiming_lifecycle_behavior",
    "tests_passing": 20,
    "tests_failing": 0,
    "files_changed": ["CHANGELOG.md", "USER-MANUAL.md", "docs/index.html", "TDD_LOG.md"],
    "commit_sha": "7ea3afa",
    "notes": "Updated current-facing docs and changelog to describe schema and Alembic scaffolding without claiming lifecycle behavior."
  },
  {
    "milestone": 2,
    "iteration": "audit-fix",
    "target_test": "tests/test_milestone_2_schema_and_migrations.py::test_alembic_command_upgrades_real_pgvector_database",
    "tests_passing": 21,
    "tests_failing": 0,
    "files_changed": ["civicclerk/migrations/env.py", "civicclerk/migrations/guards.py", "civicclerk/migrations/versions/civicclerk_0001_schema.py", "tests/test_milestone_2_schema_and_migrations.py", "pyproject.toml", "TDD_LOG.md"],
    "commit_sha": "fd77804",
    "notes": "Fixed Alembic runtime path by running CivicCore migrations in an isolated process, added schema-aware create-table guard, and replaced mocked migration smoke with a pgvector-backed integration test."
  },
  {
    "milestone": 3,
    "iteration": 1,
    "target_test": "tests/test_milestone_3_agenda_item_lifecycle.py::test_agenda_item_lifecycle_matrix_allows_only_canonical_edges",
    "tests_passing": 0,
    "tests_failing": 124,
    "files_changed": ["tests/test_milestone_3_agenda_item_lifecycle.py", "TDD_LOG.md"],
    "commit_sha": "5cbfc36",
    "notes": "Added failing agenda item lifecycle contract: full transition matrix plus API audit behavior for valid, invalid, and unknown-status transitions."
  },
  {
    "milestone": 3,
    "iteration": 2,
    "target_test": "tests/test_milestone_3_agenda_item_lifecycle.py",
    "tests_passing": 125,
    "tests_failing": 0,
    "files_changed": ["civicclerk/agenda_lifecycle.py", "civicclerk/main.py", "README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "tests/test_milestone_3_agenda_item_lifecycle.py", "TDD_LOG.md"],
    "commit_sha": "b487a79",
    "notes": "Implemented agenda item lifecycle enforcement and current-facing documentation updates without starting meeting lifecycle scope."
  },
  {
    "milestone": 4,
    "iteration": 1,
    "target_test": "tests/test_milestone_4_meeting_lifecycle.py",
    "tests_passing": 0,
    "tests_failing": 152,
    "files_changed": ["tests/test_milestone_4_meeting_lifecycle.py", "TDD_LOG.md"],
    "commit_sha": "e3b3d74",
    "notes": "Added failing meeting lifecycle contract: full transition matrix plus emergency/special, closed/executive, cancellation, API audit, and docs accuracy coverage."
  },
  {
    "milestone": 4,
    "iteration": 2,
    "target_test": "tests/test_milestone_4_meeting_lifecycle.py",
    "tests_passing": 153,
    "tests_failing": 0,
    "files_changed": ["civicclerk/meeting_lifecycle.py", "civicclerk/main.py", "README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "tests/test_milestone_1_runtime_foundation.py", "TDD_LOG.md"],
    "commit_sha": "c04466e",
    "notes": "Implemented meeting lifecycle enforcement and current-facing documentation updates without starting packet, notice, vote, minutes, archive, or UI workflow scope."
  },
  {
    "milestone": 4,
    "iteration": 3,
    "target_test": "python -m pytest -q && bash scripts/verify-docs.sh && python scripts/check-civiccore-placeholder-imports.py && python -m ruff check .",
    "tests_passing": 298,
    "tests_failing": 0,
    "files_changed": ["README.md", "docs/index.html", "docs/screenshots/milestone4-desktop.png", "docs/screenshots/milestone4-mobile.png", "MILESTONE_4_DONE.md", "TDD_LOG.md"],
    "commit_sha": "908588b",
    "notes": "Captured desktop/mobile browser QA evidence, fixed mobile landing-page clipping found during QA, and recorded Milestone 4 completion evidence."
  },
  {
    "milestone": 4,
    "iteration": "audit-fix",
    "target_test": "tests/test_milestone_4_meeting_lifecycle.py::test_emergency_and_special_meeting_type_casing_cannot_bypass_notice_basis",
    "tests_passing": 303,
    "tests_failing": 0,
    "files_changed": ["civicclerk/meeting_lifecycle.py", "tests/test_milestone_4_meeting_lifecycle.py", "TDD_LOG.md", "MILESTONE_4_DONE.md"],
    "commit_sha": "d20b9a0",
    "notes": "Normalized meeting_type before statutory-basis guardrails and added regression coverage for mixed-case emergency, special, closed-session, and executive meeting types."
  },
  {
    "milestone": 5,
    "iteration": 1,
    "target_test": "tests/test_milestone_5_packet_notice_compliance.py",
    "tests_passing": 0,
    "tests_failing": 9,
    "files_changed": ["tests/test_milestone_5_packet_notice_compliance.py", "TDD_LOG.md"],
    "commit_sha": "74f7dd3",
    "notes": "Added failing packet snapshot and notice compliance contract covering versioning, actionable warnings, statutory basis, human approval, API behavior, and docs accuracy."
  },
  {
    "milestone": 5,
    "iteration": 2,
    "target_test": "tests/test_milestone_5_packet_notice_compliance.py",
    "tests_passing": 312,
    "tests_failing": 0,
    "files_changed": ["civicclerk/packet_notice.py", "civicclerk/meeting_lifecycle.py", "civicclerk/main.py", "README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "tests/test_milestone_1_runtime_foundation.py", "docs/screenshots/milestone5-desktop.png", "docs/screenshots/milestone5-mobile.png", "TDD_LOG.md"],
    "commit_sha": "b14dfa8",
    "notes": "Implemented versioned packet snapshots, operator-configured notice compliance checks, human-approved public posting, current-facing docs, and desktop/mobile browser QA evidence without starting vote, minutes, archive, UI, or AI workflow scope."
  },
  {
    "milestone": 5,
    "iteration": "audit-fix",
    "target_test": "tests/test_milestone_5_packet_notice_compliance.py::test_api_notice_check_rejects_naive_scheduled_start_without_500",
    "tests_passing": 313,
    "tests_failing": 0,
    "files_changed": ["civicclerk/main.py", "tests/test_milestone_5_packet_notice_compliance.py", "TDD_LOG.md", "MILESTONE_5_DONE.md"],
    "commit_sha": "7295f56",
    "notes": "Rejected timezone-naive scheduled_start values with actionable 422 responses before notice compliance comparisons can crash."
  },
  {
    "milestone": 6,
    "iteration": 1,
    "target_test": "tests/test_milestone_6_motion_vote_action_capture.py",
    "tests_passing": 0,
    "tests_failing": 5,
    "files_changed": ["tests/test_milestone_6_motion_vote_action_capture.py"],
    "commit_sha": "131ae4a",
    "notes": "Added failing motion, vote, and action-item capture contract covering immutable captured records, append-only corrections, action-item source links, actionable errors, API behavior, and docs accuracy."
  },
  {
    "milestone": 6,
    "iteration": 2,
    "target_test": "tests/test_milestone_6_motion_vote_action_capture.py tests/test_milestone_1_runtime_foundation.py",
    "tests_passing": 15,
    "tests_failing": 0,
    "files_changed": ["civicclerk/motion_vote.py", "civicclerk/main.py", "README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "tests/test_milestone_1_runtime_foundation.py", "docs/screenshots/milestone6-desktop.png", "docs/screenshots/milestone6-mobile.png"],
    "commit_sha": "7b4d813",
    "notes": "Implemented immutable motion and vote capture, append-only correction endpoints, action-item capture linked to source motions, current-facing docs, root endpoint update, and desktop/mobile browser QA evidence without starting minutes, archive, UI, or AI workflow scope."
  },
  {
    "milestone": 6,
    "iteration": "audit-fix",
    "target_test": "tests/test_milestone_6_motion_vote_action_capture.py::test_action_item_requires_source_motion_with_actionable_error",
    "tests_passing": 319,
    "tests_failing": 0,
    "files_changed": ["civicclerk/main.py", "tests/test_milestone_6_motion_vote_action_capture.py", "TDD_LOG.md", "MILESTONE_6_DONE.md"],
    "commit_sha": "86ae644",
    "notes": "Required action items to reference a captured source motion so the shipped action-item claim cannot create unlinked outcomes."
  },
  {
    "milestone": 7,
    "iteration": 1,
    "target_test": "tests/test_milestone_7_minutes_citations.py",
    "tests_passing": 0,
    "tests_failing": 6,
    "files_changed": ["tests/test_milestone_7_minutes_citations.py"],
    "commit_sha": "6515a6f",
    "notes": "Added failing minutes citation contract covering sentence-level citations, unknown citation rejection, provenance, human approver requirement, no auto-posting, and docs accuracy."
  },
  {
    "milestone": 7,
    "iteration": 2,
    "target_test": "tests/test_milestone_7_minutes_citations.py tests/test_milestone_1_runtime_foundation.py",
    "tests_passing": 16,
    "tests_failing": 0,
    "files_changed": ["civicclerk/minutes.py", "civicclerk/main.py", "README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "tests/test_milestone_1_runtime_foundation.py", "docs/screenshots/milestone7-desktop.png", "docs/screenshots/milestone7-mobile.png"],
    "commit_sha": "1c9074a",
    "notes": "Implemented citation-gated minutes draft capture with provenance, rejection of uncited or unknown-cited output, no automatic public posting, current-facing docs, root endpoint update, and desktop/mobile browser QA evidence without starting archive or UI workflow scope."
  },
  {
    "milestone": 7,
    "iteration": "audit-fix",
    "target_test": "python -m pytest -q",
    "tests_passing": 325,
    "tests_failing": 0,
    "files_changed": ["tests/conftest.py", "TDD_LOG.md", "MILESTONE_7_DONE.md"],
    "commit_sha": "72a2e47",
    "notes": "Set Windows tests to use the selector event-loop policy so full-suite async tests avoid Proactor self-pipe socket exhaustion."
  },
  {
    "milestone": 8,
    "iteration": 1,
    "target_test": "tests/test_milestone_8_public_archive.py",
    "tests_passing": 0,
    "tests_failing": 5,
    "files_changed": ["tests/test_milestone_8_public_archive.py"],
    "commit_sha": "4288fed",
    "notes": "Added failing public archive contract covering public calendar filtering, public detail not-found behavior, anonymous closed-session leak prevention, permission-aware staff/clerk search behavior, and docs accuracy."
  },
  {
    "milestone": 8,
    "iteration": 2,
    "target_test": "tests/test_milestone_8_public_archive.py tests/test_milestone_1_runtime_foundation.py",
    "tests_passing": 15,
    "tests_failing": 0,
    "files_changed": ["civicclerk/public_archive.py", "civicclerk/main.py", "README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "tests/test_milestone_1_runtime_foundation.py", "docs/screenshots/milestone8-desktop.png", "docs/screenshots/milestone8-mobile.png"],
    "commit_sha": "e8aa7ab",
    "notes": "Implemented permission-aware public meeting calendar, public detail, and archive search endpoints with closed-session filtering, current-facing docs, root endpoint update, and desktop/mobile browser QA evidence without starting prompt YAML, evaluation, full UI, or database-backed archive persistence scope."
  },
  {
    "milestone": 9,
    "iteration": 1,
    "target_test": "tests/test_milestone_9_prompt_yaml_evals.py",
    "tests_passing": 0,
    "tests_failing": 6,
    "files_changed": ["tests/test_milestone_9_prompt_yaml_evals.py"],
    "commit_sha": "27accb8",
    "notes": "Added failing prompt YAML and evaluation harness contract covering YAML loading/rendering, minutes prompt-version enforcement, offline eval execution, CI wiring, no hardcoded policy prompt strings, and docs accuracy."
  },
  {
    "milestone": 9,
    "iteration": 2,
    "target_test": "tests/test_milestone_9_prompt_yaml_evals.py tests/test_milestone_7_minutes_citations.py tests/test_milestone_1_runtime_foundation.py",
    "tests_passing": 22,
    "tests_failing": 0,
    "files_changed": [".github/workflows/ci.yml", "civicclerk/prompt_library.py", "civicclerk/prompt_evals.py", "civicclerk/minutes.py", "civicclerk/main.py", "prompts/minutes_draft.yaml", "scripts/run-prompt-evals.py", "README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "tests/test_milestone_1_runtime_foundation.py", "tests/test_milestone_7_minutes_citations.py", "docs/screenshots/milestone9-desktop.png", "docs/screenshots/milestone9-mobile.png"],
    "commit_sha": "dfddc2b",
    "notes": "Implemented the YAML prompt library, offline prompt evaluation harness, CI prompt-eval gate, minutes prompt-version provenance enforcement, current-facing docs, root endpoint update, and desktop/mobile browser QA evidence without starting connector/import or UI workflow scope."
  },
  {
    "milestone": 10,
    "iteration": 1,
    "target_test": "tests/test_milestone_10_connectors_imports.py",
    "tests_passing": 0,
    "tests_failing": 9,
    "files_changed": ["tests/test_milestone_10_connectors_imports.py"],
    "commit_sha": "6356a28",
    "notes": "Added failing connector/import contract covering Granicus, Legistar, PrimeGov, and NovusAGENDA local payload normalization, source provenance, no outbound network dependency, actionable failures, API behavior, and docs accuracy."
  },
  {
    "milestone": 10,
    "iteration": 2,
    "target_test": "tests/test_milestone_10_connectors_imports.py tests/test_milestone_1_runtime_foundation.py",
    "tests_passing": 19,
    "tests_failing": 0,
    "files_changed": ["civicclerk/connectors.py", "civicclerk/main.py", "README.md", "USER-MANUAL.md", "docs/index.html", "CHANGELOG.md", "tests/test_milestone_1_runtime_foundation.py", "docs/screenshots/milestone10-desktop.png", "docs/screenshots/milestone10-mobile.png"],
    "commit_sha": "a9450bd",
    "notes": "Implemented local-first connector import normalization with source provenance, actionable connector errors, API endpoint, current-facing docs, root endpoint update, and desktop/mobile browser QA evidence without starting live sync, full UI, or database-backed connector persistence scope."
  },
  {
    "milestone": 11,
    "iteration": 1,
    "target_test": "tests/test_milestone_11_accessibility_browser_qa.py",
    "tests_passing": 0,
    "tests_failing": 5,
    "files_changed": ["tests/test_milestone_11_accessibility_browser_qa.py"],
    "commit_sha": "9e957e0",
    "notes": "Added failing browser QA gate contract covering required rendered states, keyboard/focus/contrast/console checks, screenshot evidence, CI gate wiring, landing-page focus style, and docs accuracy."
  },
  {
    "milestone": 11,
    "iteration": 2,
    "target_test": "tests/test_milestone_11_accessibility_browser_qa.py tests/test_milestone_1_runtime_foundation.py",
    "tests_passing": 15,
    "tests_failing": 0,
    "files_changed": [".github/workflows/ci.yml", "docs/browser-qa/milestone11-checklist.md", "docs/browser-qa/states.html", "docs/screenshots/milestone11-browser-qa-desktop.png", "docs/screenshots/milestone11-browser-qa-mobile.png", "scripts/verify-browser-qa.py", "scripts/verify-docs.sh", "docs/index.html", "README.md", "USER-MANUAL.md", "CHANGELOG.md", "civicclerk/main.py", "tests/test_milestone_1_runtime_foundation.py"],
    "commit_sha": "032fe48",
    "notes": "Implemented browser QA fixture, gate script, CI wiring, focus-visible styling, current-facing docs, root endpoint update, and desktop/mobile screenshot evidence without starting release/version-bump scope."
  },
  {
    "milestone": 12,
    "iteration": 1,
    "target_test": "tests/test_milestone_12_release.py",
    "tests_passing": 0,
    "tests_failing": 5,
    "files_changed": ["tests/test_milestone_12_release.py"],
    "commit_sha": "9b6914e",
    "notes": "Added failing v0.1.0 release contract covering synchronized version surfaces, health/root runtime version, release gate script, build artifacts, checksums, workflow wiring, and documentation references."
  },
  {
    "milestone": 12,
    "iteration": 2,
    "target_test": "tests/test_milestone_12_release.py tests/test_milestone_1_runtime_foundation.py",
    "tests_passing": 15,
    "tests_failing": 0,
    "files_changed": [".github/workflows/release.yml", "CHANGELOG.md", "README.md", "USER-MANUAL.md", "civicclerk/__init__.py", "civicclerk/main.py", "docs/index.html", "docs/screenshots/milestone12-desktop.png", "docs/screenshots/milestone12-mobile.png", "pyproject.toml", "scripts/verify-docs.sh", "scripts/verify-release.sh", "tests/test_milestone_1_runtime_foundation.py", "tests/test_milestone_12_release.py"],
    "commit_sha": "bd7fbae",
    "notes": "Prepared the CivicClerk v0.1.0 release: synchronized version surfaces, added release workflow and verify-release gate, built wheel/sdist with SHA256 checksums, updated current-facing docs and root endpoint, and captured desktop/mobile browser QA evidence."
  },
  {
    "milestone": 12,
    "iteration": 3,
    "target_test": "tests/test_milestone_12_release.py::test_release_workflow_and_docs_reference_v010_release",
    "tests_passing": 5,
    "tests_failing": 0,
    "files_changed": [".github/workflows/release.yml", "tests/test_milestone_12_release.py"],
    "commit_sha": "d798bb0",
    "notes": "Tightened the tag-triggered release workflow so it publishes dist artifacts to a GitHub Release with contents:write permissions after verify-release.sh passes."
  },
  {
    "milestone": 12,
    "iteration": 4,
    "target_test": "bash scripts/verify-release.sh",
    "tests_passing": 350,
    "tests_failing": 0,
    "files_changed": ["scripts/verify-release.sh", "TDD_LOG.md", "MILESTONE_12_DONE.md"],
    "commit_sha": "pending",
    "notes": "Made release builds reproducible with SOURCE_DATE_EPOCH so the generated sdist checksum remains stable across repeated release-gate runs."
  }
]
```
