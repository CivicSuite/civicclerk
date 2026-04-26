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
    "commit_sha": "f3c0b98",
    "notes": "Expanded CI from docs-only to install package, run pytest, verify docs, and check placeholder imports."
  }
]
```
