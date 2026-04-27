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
    "commit_sha": "pending",
    "notes": "Required action items to reference a captured source motion so the shipped action-item claim cannot create unlinked outcomes."
  }
]
```
