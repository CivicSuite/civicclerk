"""Task 5: HTTP-level proof that the legal record survives an API restart."""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient

import civicclerk.main as main_module
from civicclerk import public_archive as public_archive_module

ROOT = Path(__file__).resolve().parents[1]

_RESTART_GLOBALS = (
    "_motion_vote_repository",
    "_motion_vote_db_url",
    "_minutes_draft_repository",
    "_minutes_draft_db_url",
    "_public_archive_repository",
    "_public_archive_db_url",
    "_public_comment_repository",
    "_public_comment_db_url",
    "_meeting_store",
    "_meeting_db_url",
)


import pytest


@pytest.fixture(autouse=True)
def _restore_backend_globals():
    """Snapshot and restore the getter caches this file's restart simulation nulls.

    Without this, _simulate_process_restart() leaks None-d module globals into
    later test files (observed: the staff UI test inheriting a gutted meeting
    store when run after this file).
    """

    saved = {name: getattr(main_module, name) for name in _RESTART_GLOBALS}
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(main_module, name, value)


def _simulate_process_restart() -> None:
    """Drop every cached repository engine so the next request rebuilds from disk.

    This is the acceptance pattern: instance A wrote through the API, the
    cached singletons are discarded (process-style restart), and instance B
    must serve the same legal record from the database with no in-memory
    fallback involved.
    """

    for repository in (
        main_module._motion_vote_repository,
        main_module._minutes_draft_repository,
        main_module._public_archive_repository,
        main_module._public_comment_repository,
        main_module._meeting_store,
    ):
        engine = getattr(repository, "engine", None)
        if engine is not None:
            engine.dispose()
    main_module._motion_vote_repository = None
    main_module._motion_vote_db_url = None
    main_module._minutes_draft_repository = None
    main_module._minutes_draft_db_url = None
    main_module._public_archive_repository = None
    main_module._public_archive_db_url = None
    main_module._public_comment_repository = None
    main_module._public_comment_db_url = None
    main_module._meeting_store = None
    main_module._meeting_db_url = None


def _seed_archive_meeting_referent(db_url: str, meeting_id: str) -> None:
    """Insert the civicclerk.meetings parent row publish() pre-checks.

    The live meeting lifecycle persists to ``meeting_records`` while the
    public archive FK (migration 0014) references canonical
    ``civicclerk.meetings``; until those tables are unified, archive
    deployments mirror the meeting id — the same pattern demo_seed and the
    archive persistence tests use.
    """

    engine = sa.create_engine(db_url, future=True)
    if engine.dialect.name == "sqlite":
        engine = engine.execution_options(schema_translate_map={"civicclerk": None})
    public_archive_module.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            public_archive_module.meetings_table.insert().values(id=meeting_id)
        )
    engine.dispose()


async def test_legal_record_survives_api_restart_when_db_env_vars_set(
    monkeypatch, tmp_path
) -> None:
    archive_db_url = f"sqlite:///{tmp_path / 'archive.db'}"
    monkeypatch.setenv("CIVICCLERK_MEETING_DB_URL", f"sqlite:///{tmp_path / 'meetings.db'}")
    monkeypatch.setenv("CIVICCLERK_MOTION_VOTE_DB_URL", f"sqlite:///{tmp_path / 'motions.db'}")
    monkeypatch.setenv("CIVICCLERK_MINUTES_DB_URL", f"sqlite:///{tmp_path / 'minutes.db'}")
    monkeypatch.setenv("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL", archive_db_url)
    _simulate_process_restart()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Persistence Proof Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-06-10T19:00:00Z",
            },
        )
        meeting_id = meeting.json()["id"]
        motion = await client.post(
            f"/meetings/{meeting_id}/motions",
            json={
                "text": "Move to approve the sidewalk contract.",
                "actor": "clerk@example.gov",
                "seconded_by": "Council Member Patel",
            },
        )
        motion_id = motion.json()["id"]
        vote = await client.post(
            f"/motions/{motion_id}/votes",
            json={
                "voter_name": "Council Member Rivera",
                "vote": "aye",
                "actor": "clerk@example.gov",
            },
        )
        action_item = await client.post(
            f"/meetings/{meeting_id}/action-items",
            json={
                "description": "Notify the contractor of the award.",
                "assigned_to": "Public Works Director",
                "source_motion_id": motion_id,
                "actor": "clerk@example.gov",
            },
        )
        draft = await client.post(
            f"/meetings/{meeting_id}/minutes/drafts",
            json={
                "model": "ollama/gemma4",
                "prompt_version": "minutes_draft@0.1.0",
                "human_approver": "clerk@example.gov",
                "source_materials": [
                    {
                        "source_id": "motion-1",
                        "label": "Captured motion",
                        "text": "Council approved the sidewalk contract 4-1.",
                    }
                ],
                "sentences": [
                    {
                        "text": "Council approved the sidewalk contract 4-1.",
                        "citations": ["motion-1"],
                    }
                ],
            },
        )
        _seed_archive_meeting_referent(archive_db_url, meeting_id)
        record = await client.post(
            f"/meetings/{meeting_id}/public-record",
            json={
                "title": "Persistence Proof Meeting",
                "visibility": "public",
                "posted_agenda": "Agenda text.",
                "posted_packet": "Packet text.",
                "approved_minutes": "Minutes text.",
                "public_comment_enabled": True,
            },
        )
        comment = await client.post(
            f"/public/meetings/{record.json()['id']}/comments",
            json={
                "commenter_name": "Resident Lee",
                "comment": "Please add a crosswalk.",
            },
        )

    assert motion.status_code == 201
    assert vote.status_code == 201
    assert action_item.status_code == 201, action_item.json()
    assert draft.status_code == 201, draft.json()
    assert record.status_code == 201, record.json()
    assert comment.status_code == 201

    _simulate_process_restart()

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        motions_after = await client.get(f"/meetings/{meeting_id}/motions")
        votes_after = await client.get(f"/motions/{motion_id}/votes")
        action_items_after = await client.get(f"/meetings/{meeting_id}/action-items")
        drafts_after = await client.get(f"/meetings/{meeting_id}/minutes/drafts")
        calendar_after = await client.get("/public/meetings")
        detail_after = await client.get(f"/public/meetings/{record.json()['id']}")
        comments_after = await client.get(
            f"/public/meetings/{record.json()['id']}/comments"
        )
        put_after = await client.put(
            f"/motions/{motion_id}",
            json={"text": "Rewrite the record after restart."},
        )

    assert [m["id"] for m in motions_after.json()["motions"]] == [motion_id]
    assert motions_after.json()["motions"][0]["captured"] is True
    assert motions_after.json()["motions"][0]["seconded_by"] == "Council Member Patel"
    assert [v["id"] for v in votes_after.json()["votes"]] == [vote.json()["id"]]
    assert votes_after.json()["votes"][0]["vote"] == "aye"
    assert [a["id"] for a in action_items_after.json()["action_items"]] == [
        action_item.json()["id"]
    ]
    assert action_items_after.json()["action_items"][0]["source_motion_id"] == motion_id
    assert [d["id"] for d in drafts_after.json()["drafts"]] == [draft.json()["id"]]
    assert drafts_after.json()["drafts"][0]["provenance"]["model"] == "ollama/gemma4"
    assert drafts_after.json()["drafts"][0]["adopted"] is False
    assert drafts_after.json()["drafts"][0]["posted"] is False
    assert record.json()["id"] in [m["id"] for m in calendar_after.json()["meetings"]]
    assert detail_after.status_code == 200
    assert [c["id"] for c in comments_after.json()["comments"]] == [comment.json()["id"]]
    assert put_after.status_code == 409
    assert put_after.json()["detail"]["message"] == "Captured motions are immutable."


def test_readme_recovery_notice_documents_persisted_legal_record() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "CIVICCLERK_MOTION_VOTE_DB_URL" in readme
    assert "CIVICCLERK_MINUTES_DB_URL" in readme
    assert "CIVICCLERK_PUBLIC_ARCHIVE_DB_URL" in readme
    assert "does not survive a restart" in readme
    assert "Phase 1b" in readme
