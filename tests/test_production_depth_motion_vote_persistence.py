from __future__ import annotations

import importlib.util
import inspect
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa

from civicclerk import motion_vote as motion_vote_module
from civicclerk.motion_vote import MotionVoteRepository

ROOT = Path(__file__).resolve().parents[1]


def freeze_module_clock(monkeypatch, module) -> datetime:
    """Pin a module's datetime.now so every insert shares one created_at tick.

    Same-timestamp rows are the production failure mode this hammers: with
    (created_at, id) ordering the uuid4 id decided the order randomly.
    """

    frozen = datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001 - mirrors datetime.now signature
            return frozen if tz is not None else frozen.replace(tzinfo=None)

    monkeypatch.setattr(module, "datetime", FrozenDatetime)
    return frozen


def test_motions_votes_action_items_persist_across_repository_instances(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'motion-vote.db'}"
    meeting_id = str(uuid4())
    agenda_item_id = str(uuid4())

    first = MotionVoteRepository(db_url=db_url)
    motion = first.capture_motion(
        meeting_id=meeting_id,
        agenda_item_id=agenda_item_id,
        text="Move to approve the packet as presented.",
        actor="clerk@example.gov",
        seconded_by="  Council Member Patel  ",
    )
    vote = first.capture_vote(
        motion_id=motion.id,
        voter_name="Council Member Rivera",
        vote=" AYE ",
        actor="clerk@example.gov",
    )
    action_item = first.create_action_item(
        meeting_id=meeting_id,
        description="Publish signed contract award notice.",
        assigned_to="Public Works",
        source_motion_id=motion.id,
        actor="clerk@example.gov",
    )

    second = MotionVoteRepository(db_url=db_url)
    motions = second.list_motions(meeting_id)
    votes = second.list_votes(motion.id)
    action_items = second.list_action_items(meeting_id)

    assert [m.id for m in motions] == [motion.id]
    assert motions[0].public_dict() == {
        "id": motion.id,
        "meeting_id": meeting_id,
        "agenda_item_id": agenda_item_id,
        "text": "Move to approve the packet as presented.",
        "actor": "clerk@example.gov",
        "seconded_by": "Council Member Patel",
        "correction_of_id": None,
        "correction_reason": None,
        "captured": True,
    }
    assert [v.id for v in votes] == [vote.id]
    assert votes[0].vote == "aye"
    assert votes[0].actor == "clerk@example.gov"
    assert [a.id for a in action_items] == [action_item.id]
    assert action_items[0].status == "OPEN"
    assert action_items[0].actor == "clerk@example.gov"
    assert action_items[0].source_motion_id == motion.id


def test_corrections_are_append_only_and_listed_in_insertion_order(tmp_path) -> None:
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'corrections.db'}")
    meeting_id = str(uuid4())
    original = repo.capture_motion(
        meeting_id=meeting_id,
        text="Move to award the contract.",
        actor="clerk@example.gov",
        seconded_by="Council Member Patel",
    )
    correction = repo.correct_motion(
        original_motion_id=original.id,
        text="Move to award the contract as amended.",
        actor="clerk@example.gov",
        reason="Clerk correction after audio review.",
    )

    assert correction is not None
    assert correction.correction_of_id == original.id
    assert correction.seconded_by == "Council Member Patel"
    assert [m.id for m in repo.list_motions(meeting_id)] == [original.id, correction.id]

    vote = repo.capture_vote(
        motion_id=original.id,
        voter_name="Council Member Rivera",
        vote="aye",
        actor="clerk@example.gov",
    )
    vote_correction = repo.correct_vote(
        original_vote_id=vote.id,
        vote="abstain",
        actor="clerk@example.gov",
        reason="Member clarified abstention.",
    )
    assert vote_correction is not None
    assert vote_correction.correction_of_id == vote.id
    assert vote_correction.voter_name == "Council Member Rivera"
    assert vote_correction.vote == "abstain"
    assert [v.id for v in repo.list_votes(original.id)] == [vote.id, vote_correction.id]

    assert repo.get_motion("not-a-uuid") is None
    assert repo.get_vote("not-a-uuid") is None
    assert repo.correct_motion(
        original_motion_id=str(uuid4()), text="x", actor="a", reason="r"
    ) is None
    assert repo.audit_chain.verify()


def test_repository_lists_recent_outcome_summaries(tmp_path) -> None:
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'outcomes.db'}")
    meeting_one = str(uuid4())
    meeting_two = str(uuid4())
    repo.capture_motion(
        meeting_id=meeting_one,
        text="Move to approve sidewalk repairs.",
        actor="clerk@example.gov",
    )
    second = repo.capture_motion(
        meeting_id=meeting_two,
        text="Move to award the paving contract.",
        actor="deputy@example.gov",
    )
    repo.capture_vote(
        motion_id=second.id,
        voter_name="Council Member Rivera",
        vote="aye",
        actor="clerk@example.gov",
    )
    repo.create_action_item(
        meeting_id=meeting_two,
        description="Schedule contract signing.",
        actor="clerk@example.gov",
        source_motion_id=second.id,
    )

    recent = repo.list_recent_outcomes(limit=1)

    assert len(recent) == 1
    assert recent[0].motion_id == second.id
    assert recent[0].meeting_id == meeting_two
    assert recent[0].vote_count == 1
    assert recent[0].action_item_count == 1
    assert recent[0].status == "CAPTURED"


def test_concurrent_motion_capture_keeps_audit_chain_intact(tmp_path) -> None:
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'concurrent.db'}")
    meeting_id = str(uuid4())

    def capture_batch(worker_index: int) -> None:
        for sequence in range(25):
            repo.capture_motion(
                meeting_id=meeting_id,
                text=f"Motion from worker {worker_index} #{sequence}.",
                actor="clerk@example.gov",
            )

    # Force frequent thread switches so unsynchronized read-last-hash-then-append
    # interleavings surface deterministically instead of once a month in production.
    original_interval = sys.getswitchinterval()
    try:
        sys.setswitchinterval(1e-6)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(capture_batch, range(8)))
    finally:
        sys.setswitchinterval(original_interval)

    assert len(repo.list_motions(meeting_id)) == 200
    assert len(repo.audit_chain.events) == 200
    assert repo.audit_chain.verify()


def test_capture_vote_with_unknown_motion_returns_none_without_orphan_row(tmp_path) -> None:
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'fk-votes.db'}")
    missing_motion_id = str(uuid4())

    result = repo.capture_vote(
        motion_id=missing_motion_id,
        voter_name="Council Member Rivera",
        vote="aye",
        actor="clerk@example.gov",
    )

    assert result is None
    assert repo.list_votes(missing_motion_id) == []
    assert repo.audit_chain.events == []
    assert repo.audit_chain.verify()


def test_create_action_item_with_unknown_source_motion_returns_none(tmp_path) -> None:
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'fk-actions.db'}")
    meeting_id = str(uuid4())

    result = repo.create_action_item(
        meeting_id=meeting_id,
        description="Publish signed contract award notice.",
        actor="clerk@example.gov",
        source_motion_id=str(uuid4()),
    )

    assert result is None
    assert repo.list_action_items(meeting_id) == []
    assert repo.audit_chain.events == []
    assert repo.audit_chain.verify()


def test_capture_motion_narrows_invalid_agenda_item_id_to_none(tmp_path) -> None:
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'narrowing.db'}")
    meeting_id = str(uuid4())

    motion = repo.capture_motion(
        meeting_id=meeting_id,
        agenda_item_id="not-a-uuid",
        text="Move to approve the packet as presented.",
        actor="clerk@example.gov",
    )

    assert motion.agenda_item_id is None
    persisted = repo.get_motion(motion.id)
    assert persisted is not None
    assert persisted.agenda_item_id is None


def test_failed_insert_leaves_no_phantom_audit_event(tmp_path) -> None:
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'phantom.db'}")

    with pytest.raises(sa.exc.IntegrityError):
        repo.capture_motion(
            meeting_id=str(uuid4()),
            text=None,  # type: ignore[arg-type]  # violates NOT NULL on motions.text
            actor="clerk@example.gov",
        )

    assert repo.audit_chain.events == []
    assert repo.audit_chain.verify()


def test_same_timestamp_captures_preserve_insertion_order(tmp_path, monkeypatch) -> None:
    """Rows captured within one timestamp tick must list in insertion order.

    Before capture_seq, list reads tiebroke (created_at, id) on a random
    uuid4, so this test failed with near-certainty (1/24! chance of passing).
    """

    freeze_module_clock(monkeypatch, motion_vote_module)
    repo = MotionVoteRepository(db_url=f"sqlite:///{tmp_path / 'same-tick.db'}")
    meeting_id = str(uuid4())

    motions = [
        repo.capture_motion(
            meeting_id=meeting_id,
            text=f"Motion #{index}.",
            actor="clerk@example.gov",
        )
        for index in range(24)
    ]
    assert [m.id for m in repo.list_motions(meeting_id)] == [m.id for m in motions]

    votes = [
        repo.capture_vote(
            motion_id=motions[0].id,
            voter_name=f"Council Member {index}",
            vote="aye",
            actor="clerk@example.gov",
        )
        for index in range(24)
    ]
    assert [v.id for v in repo.list_votes(motions[0].id)] == [v.id for v in votes]

    action_items = [
        repo.create_action_item(
            meeting_id=meeting_id,
            description=f"Action item #{index}.",
            actor="clerk@example.gov",
        )
        for index in range(24)
    ]
    assert [a.id for a in repo.list_action_items(meeting_id)] == [
        a.id for a in action_items
    ]

    recent = repo.list_recent_outcomes(limit=24)
    assert [s.motion_id for s in recent] == [m.id for m in reversed(motions)]


def test_migration_0015_adds_capture_seq_with_legacy_backfill() -> None:
    path = (
        ROOT
        / "civicclerk"
        / "migrations"
        / "versions"
        / "civicclerk_0015_capture_seq.py"
    )
    assert path.exists(), "Missing migration: civicclerk_0015_capture_seq.py"
    spec = importlib.util.spec_from_file_location("civicclerk_0015_capture_seq", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "civicclerk_0015_capture_seq"
    assert module.down_revision == "civicclerk_0014_public_records"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    upgrade_source = inspect.getsource(module.upgrade)
    for table_name in (
        "motions",
        "votes",
        "action_items",
        "minutes",
        "public_meeting_records",
        "public_comments",
    ):
        assert f'"{table_name}"' in inspect.getsource(module) or table_name in upgrade_source
    assert "capture_seq" in upgrade_source
    # Legacy rows must keep their best-known order when backfilled.
    assert "created_at" in upgrade_source and "row_number" in upgrade_source


def test_migration_0012_adds_action_item_actor_and_extends_chain() -> None:
    path = (
        ROOT
        / "civicclerk"
        / "migrations"
        / "versions"
        / "civicclerk_0012_action_item_actor.py"
    )
    assert path.exists(), "Missing migration: civicclerk_0012_action_item_actor.py"
    spec = importlib.util.spec_from_file_location("civicclerk_0012_action_item_actor", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "civicclerk_0012_action_actor"
    assert module.down_revision == "civicclerk_0011_data_model"
    assert callable(module.upgrade)
    assert callable(module.downgrade)
