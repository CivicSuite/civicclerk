# Plan: clerk-persistence Phase 1 review fixes

Hard Rule 11 plan file for three code-review fixes on work/clerk-persistence-phase-1.
Scope: civicclerk/minutes.py, tests/test_production_depth_minutes_persistence.py only.

1. IMPORTANT — add `test_concurrent_draft_creation_keeps_audit_chain_intact` to
   tests/test_production_depth_minutes_persistence.py, mirroring the motion-vote
   concurrency test (8 workers x 25 create_draft on one MinutesDraftRepository over a
   SQLite file DB; sys.setswitchinterval(1e-6) as the first line inside try, restored
   in finally; assert 200 drafts, 200 chain events, audit_chain.verify()). Run 3x.
2. MINOR — extract the duplicated prompt-version + citation validation block from
   MinutesDraftStore.create_draft and MinutesDraftRepository.create_draft into
   module-level `_validate_create_inputs(...)`. Zero behavior change; prove with
   test_milestone_7_minutes_citations.py + the persistence file.
3. MINOR — document in both class docstrings that adopted_at/posted_at have no
   writer by design; mark_adopted/mark_posted deferred to Phase 1b.

Verify: pytest over the four persistence/milestone files; commit -s, no push.
