# Backup/Restore Docs Browser QA

Date: 2026-04-30

Page checked: `docs/index.html`

Evidence:

- Desktop screenshot: `docs/screenshots/backup-restore-docs-desktop.png`
- Mobile-width screenshot: `docs/screenshots/backup-restore-docs-mobile.png`
- Chrome headless DOM load returned the CivicClerk document with the backup/restore helper copy present.

Checks:

- Desktop viewport: 1440x1000.
- Mobile-width viewport: 500x844.
- User-visible copy mentions `scripts/start_backup_restore_rehearsal.ps1`, `scripts/start_backup_restore_rehearsal.sh`, `scripts/check_backup_restore_rehearsal.py`, `.backup-restore-rehearsal`, `backup/civicclerk-backup-manifest.json`, `CIVICCLERK_NOTICE_CHECKLIST_DB_URL`, and `CIVICCLERK_EXPORT_ROOT`.
- Console/runtime risk: no page JavaScript was introduced in this docs-only change; the static HTML loaded under Chrome headless.
