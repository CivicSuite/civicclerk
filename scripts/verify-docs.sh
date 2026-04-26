#!/usr/bin/env bash
set -euo pipefail

required=(
  README.md
  README.txt
  USER-MANUAL.md
  USER-MANUAL.txt
  CHANGELOG.md
  CONTRIBUTING.md
  LICENSE
  LICENSE-DOCS
  CODE_OF_CONDUCT.md
  SECURITY.md
  SUPPORT.md
  .gitignore
  docs/index.html
  docs/github-discussions-seed.md
  docs/roadmap/mvp-plan.md
  docs/architecture/ADR-0001-mvp-boundary.md
  .github/PULL_REQUEST_TEMPLATE.md
  .github/ISSUE_TEMPLATE/bug_report.md
  .github/ISSUE_TEMPLATE/feature_request.md
)

for file in "${required[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required artifact: $file" >&2
    exit 1
  fi
done

if grep -RInE 'scottconverse/civicrecords-ai|v1\.3\.0|civiccore 0\.1\.0|Phase 0 scaffold' \
  -- README.md README.txt USER-MANUAL.md USER-MANUAL.txt docs .github CHANGELOG.md CONTRIBUTING.md SECURITY.md SUPPORT.md; then
  echo "Found stale current-facing text" >&2
  exit 1
fi

echo "VERIFY-DOCS: PASSED"
