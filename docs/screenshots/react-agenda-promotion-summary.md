# React Agenda Promotion Browser QA

- Scope: Agenda Intake submit -> ready review -> promote to canonical agenda lifecycle.
- Desktop screenshot: docs/screenshots/react-agenda-promotion-desktop.png
- Mobile screenshot: docs/screenshots/react-agenda-promotion-mobile.png (recaptured from live promoted queue)
- State screenshots: docs/screenshots/react-agenda-promotion-state-loading.png, docs/screenshots/react-agenda-promotion-state-empty.png, docs/screenshots/react-agenda-promotion-state-error.png, docs/screenshots/react-agenda-promotion-state-partial.png
- Console errors: 0
- Console warnings: 0
- Page exceptions: 0
- Keyboard/focus evidence: {"activeTag":"BUTTON","activeText":"A Agenda intake","focusableCount":31}
- Copy evidence: {"hasPromotionCopy":true,"hasAuditHash":true,"hasAgendaLifecycle":true,"hasReviewFirst":true}
- Accessibility notes: buttons remained keyboard-focusable; pending items now show a disabled Review first action; promoted items use a disabled Promoted state; error/empty/partial copy remains actionable through shared state cards.
