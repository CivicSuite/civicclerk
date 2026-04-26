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
  }
]
```
