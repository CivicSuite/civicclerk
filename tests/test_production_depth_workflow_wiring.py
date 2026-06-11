"""Task 4 wiring: env-gated workflow repositories and idempotent demo seed."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

import civicclerk.main as main_module
from civicclerk.minutes import MinutesDraftRepository, MinutesDraftStore
from civicclerk.motion_vote import MotionVoteRepository, MotionVoteStore
from civicclerk.public_archive import (
    PublicArchiveRepository,
    PublicArchiveStore,
    PublicCommentRepository,
    PublicCommentStore,
)


def test_getters_fall_back_to_in_memory_stores_without_env(monkeypatch) -> None:
    monkeypatch.delenv("CIVICCLERK_MOTION_VOTE_DB_URL", raising=False)
    monkeypatch.delenv("CIVICCLERK_MINUTES_DB_URL", raising=False)
    monkeypatch.delenv("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL", raising=False)

    assert isinstance(main_module._get_motion_votes(), MotionVoteStore)
    assert isinstance(main_module._get_minutes_drafts(), MinutesDraftStore)
    assert isinstance(main_module._get_public_archive(), PublicArchiveStore)
    assert isinstance(main_module._get_public_comments(), PublicCommentStore)


@pytest.mark.parametrize("blank", ["", "  "], ids=["empty", "whitespace"])
def test_getters_treat_blank_env_as_unset(monkeypatch, blank) -> None:
    monkeypatch.setenv("CIVICCLERK_MOTION_VOTE_DB_URL", blank)
    monkeypatch.setenv("CIVICCLERK_MINUTES_DB_URL", blank)
    monkeypatch.setenv("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL", blank)

    assert isinstance(main_module._get_motion_votes(), MotionVoteStore)
    assert isinstance(main_module._get_minutes_drafts(), MinutesDraftStore)
    assert isinstance(main_module._get_public_archive(), PublicArchiveStore)
    assert isinstance(main_module._get_public_comments(), PublicCommentStore)


def test_getters_select_repositories_when_env_set(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_MOTION_VOTE_DB_URL", f"sqlite:///{tmp_path / 'mv.db'}")
    monkeypatch.setenv("CIVICCLERK_MINUTES_DB_URL", f"sqlite:///{tmp_path / 'mn.db'}")
    monkeypatch.setenv("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL", f"sqlite:///{tmp_path / 'pa.db'}")

    assert isinstance(main_module._get_motion_votes(), MotionVoteRepository)
    assert isinstance(main_module._get_minutes_drafts(), MinutesDraftRepository)
    assert isinstance(main_module._get_public_archive(), PublicArchiveRepository)
    assert isinstance(main_module._get_public_comments(), PublicCommentRepository)


def test_getters_cache_one_repository_per_env_value(monkeypatch, tmp_path) -> None:
    """One repository instance per process per env value; env change resets the cache."""
    cases = [
        ("CIVICCLERK_MOTION_VOTE_DB_URL", main_module._get_motion_votes, MotionVoteRepository, MotionVoteStore),
        ("CIVICCLERK_MINUTES_DB_URL", main_module._get_minutes_drafts, MinutesDraftRepository, MinutesDraftStore),
        ("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL", main_module._get_public_archive, PublicArchiveRepository, PublicArchiveStore),
        ("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL", main_module._get_public_comments, PublicCommentRepository, PublicCommentStore),
    ]
    for index, (env_name, getter, repository_type, store_type) in enumerate(cases):
        monkeypatch.setenv(env_name, f"sqlite:///{tmp_path / f'cache_a_{index}.db'}")
        first = getter()
        assert isinstance(first, repository_type)
        # Same env value -> the exact same cached instance (chain lock and
        # capture_seq MAX+1 assume one repository per process per env value).
        assert getter() is first
        monkeypatch.setenv(env_name, f"sqlite:///{tmp_path / f'cache_b_{index}.db'}")
        second = getter()
        assert isinstance(second, repository_type)
        assert second is not first
        monkeypatch.delenv(env_name)
        assert isinstance(getter(), store_type)


async def test_motion_endpoints_use_db_when_env_set(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_MEETING_DB_URL", f"sqlite:///{tmp_path / 'meetings.db'}")
    monkeypatch.setenv("CIVICCLERK_MOTION_VOTE_DB_URL", f"sqlite:///{tmp_path / 'mv.db'}")
    async with AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Wired Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-06-10T19:00:00Z",
            },
        )
        meeting_id = meeting.json()["id"]
        captured = await client.post(
            f"/meetings/{meeting_id}/motions",
            json={"text": "Move to approve.", "actor": "clerk@example.gov"},
        )
        put_attempt = await client.put(
            f"/motions/{captured.json()['id']}",
            json={"text": "Rewrite the record."},
        )
        listing = await client.get(f"/meetings/{meeting_id}/motions")

    assert captured.status_code == 201
    assert captured.json()["captured"] is True
    assert put_attempt.status_code == 409
    assert put_attempt.json()["detail"]["message"] == "Captured motions are immutable."
    assert [m["id"] for m in listing.json()["motions"]] == [captured.json()["id"]]
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'mv.db'}")
    assert [m.id for m in repo.list_motions(meeting_id)] == [captured.json()["id"]]


def test_demo_seed_is_idempotent_for_db_backed_workflow_stores(tmp_path) -> None:
    from datetime import UTC, datetime

    from civicclerk.agenda_intake import AgendaIntakeRepository
    from civicclerk.agenda_lifecycle import AgendaItemStore
    from civicclerk.demo_seed import seed_demo_data
    from civicclerk.meeting_body import MeetingBodyRepository
    from civicclerk.meeting_lifecycle import MeetingStore
    from civicclerk.notice_checklist import NoticeChecklistRepository
    from civicclerk.packet_assembly import PacketAssemblyRepository

    shared = f"sqlite:///{tmp_path / 'seed.db'}"
    kwargs = dict(
        meeting_bodies=MeetingBodyRepository(db_url=shared),
        meetings=MeetingStore(db_url=shared),
        agenda_intake=AgendaIntakeRepository(db_url=shared),
        agenda_items=AgendaItemStore(),
        packet_assemblies=PacketAssemblyRepository(db_url=shared),
        notice_checklists=NoticeChecklistRepository(db_url=shared),
        motion_votes=MotionVoteRepository(db_url=shared),
        minutes_drafts=MinutesDraftRepository(db_url=shared),
        public_archive=PublicArchiveRepository(db_url=shared),
        now=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
    )
    first = seed_demo_data(**kwargs)
    # Fresh repository instances on the same DB simulate a Compose restart.
    kwargs.update(
        motion_votes=MotionVoteRepository(db_url=shared),
        minutes_drafts=MinutesDraftRepository(db_url=shared),
        public_archive=PublicArchiveRepository(db_url=shared),
    )
    second = seed_demo_data(**kwargs)

    assert second["motion_count"] == first["motion_count"] == 1
    assert second["minutes_draft_count"] == first["minutes_draft_count"] == 1
    assert second["public_record_count"] == first["public_record_count"] == 1


def test_demo_seed_split_env_does_not_duplicate_motion_or_minutes_records(tmp_path) -> None:
    """Motion/minutes DBs persist while meetings stay in-memory: a restart hands
    the seed fresh meeting ids, so dedupe must key on demo content, not meeting id."""
    from datetime import UTC, datetime

    from civicclerk.agenda_intake import AgendaIntakeRepository
    from civicclerk.agenda_lifecycle import AgendaItemStore
    from civicclerk.demo_seed import seed_demo_data
    from civicclerk.meeting_body import MeetingBodyRepository
    from civicclerk.meeting_lifecycle import MeetingStore
    from civicclerk.notice_checklist import NoticeChecklistRepository
    from civicclerk.packet_assembly import PacketAssemblyRepository

    shared = f"sqlite:///{tmp_path / 'split-seed.db'}"

    def run_seed() -> None:
        # Fresh in-memory meeting store per run simulates a restarted process
        # whose meeting env var is unset while motion/minutes env vars are set.
        seed_demo_data(
            meeting_bodies=MeetingBodyRepository(db_url=shared),
            meetings=MeetingStore(),
            agenda_intake=AgendaIntakeRepository(db_url=shared),
            agenda_items=AgendaItemStore(),
            packet_assemblies=PacketAssemblyRepository(db_url=shared),
            notice_checklists=NoticeChecklistRepository(db_url=shared),
            motion_votes=MotionVoteRepository(db_url=shared),
            minutes_drafts=MinutesDraftRepository(db_url=shared),
            public_archive=PublicArchiveRepository(db_url=shared),
            now=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
        )

    run_seed()
    run_seed()

    motion_repo = MotionVoteRepository(db_url=shared)
    minutes_repo = MinutesDraftRepository(db_url=shared)
    assert len(motion_repo.list_recent_outcomes(limit=50)) == 1
    assert len(minutes_repo.list_recent(limit=50)) == 1


def test_demo_seed_docstring_no_longer_claims_in_memory_only() -> None:
    from civicclerk.demo_seed import seed_demo_data

    doc = (seed_demo_data.__doc__ or "").lower()
    assert "in-memory, so they are seeded" not in doc
    assert "database-backed" in doc
