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
    "commit_sha": "07512c8",
    "notes": "Fixed Alembic runtime path by running CivicCore migrations in an isolated process, added schema-aware create-table guard, and replaced mocked migration smoke with a pgvector-backed integration test."
  }
]
```
