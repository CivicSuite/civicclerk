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
    "commit_sha": "43df18e",
    "notes": "Added the minimal FastAPI app import path plus root and health responses."
  }
]
```
