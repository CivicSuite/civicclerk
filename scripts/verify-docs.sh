#!/usr/bin/env bash
# CivicClerk documentation gate.
# 1) Required artifacts exist.
# 2) Current-facing docs do not contain known stale drift markers.
set -u

fail=0

required=(
  README.md
  README.txt
  USER-MANUAL.md
  USER-MANUAL.txt
  CHANGELOG.md
  CONTRIBUTING.md
  LICENSE-CODE
  LICENSE-DOCS
  CODE_OF_CONDUCT.md
  SECURITY.md
  SUPPORT.md
  .gitignore
  docs/index.html
  docs/examples/deployment.env.example
  docs/browser-qa/milestone11-checklist.md
  docs/browser-qa/states.html
  docs/github-discussions-seed.md
  docs/RECONCILIATION.md
  docs/MILESTONES.md
  docs/roadmap/mvp-plan.md
  prompts/minutes_draft.yaml
  scripts/run-prompt-evals.py
  scripts/verify-release.sh
  scripts/verify-browser-qa.py
  scripts/check_installer_readiness.py
  scripts/check_connector_sync_readiness.py
  scripts/run_vendor_live_sync.py
  scripts/check_backup_restore_rehearsal.py
  scripts/check_protected_deployment_smoke.py
  scripts/start_backup_restore_rehearsal.ps1
  scripts/start_backup_restore_rehearsal.sh
  docs/architecture/ADR-0001-mvp-boundary.md
  docs/adr/civicclerk-adr-0001.md
  docs/adr/civicclerk-adr-0002.md
  docs/adr/civicclerk-adr-0003.md
  docs/adr/civicclerk-adr-0004.md
  docs/adr/civicclerk-adr-0005.md
  docs/adr/civicclerk-adr-0006.md
  docs/adr/civicclerk-adr-0007.md
  docs/adr/civicclerk-adr-0008.md
  .github/PULL_REQUEST_TEMPLATE.md
  .github/ISSUE_TEMPLATE/bug_report.md
  .github/ISSUE_TEMPLATE/feature_request.md
)

echo "==> Required-artifact check"
for file in "${required[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "  MISSING: $file"
    fail=1
  fi
done

echo "==> Stale current-facing strings check"
pattern='MIT|26 modules across 6 tiers|~=0\.2|civicclerk shipping|scottconverse/civicrecords-ai|v1\.3\.0|civiccore 0\.1\.0|Phase 0 scaffold'
hits=$(grep -RInE "$pattern" \
  -- README.md README.txt USER-MANUAL.md USER-MANUAL.txt docs/index.html CHANGELOG.md CONTRIBUTING.md SECURITY.md SUPPORT.md .github 2>/dev/null \
  || true)

if [[ -n "$hits" ]]; then
  echo "  STALE STRINGS FOUND:"
  echo "$hits" | sed 's/^/    /'
  fail=1
fi

for file in README.md README.txt docs/index.html; do
  if ! grep -q "connector runtime validation" "$file"; then
    echo "  MISSING CURRENT CONNECTOR CLAIM: $file"
    fail=1
  fi
done

if [[ $fail -ne 0 ]]; then
  echo "VERIFY-DOCS: FAILED"
  exit 1
fi

echo "VERIFY-DOCS: PASSED"
