from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from civicclerk.motion_vote import MotionVoteRepository

ROOT = Path(__file__).resolve().parents[1]


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


def test_migration_0012_adds_action_item_actor_and_extends_chain() -> None:
    path = (
        ROOT
        / "civicclerk"
        / "migrations"
        / "versions"
        / "civicclerk_0012_action_item_actor.py"
    )
    assert path.exists(), "Missing migration: civicclerk_0012_action_item_actor.py"
    text = path.read_text(encoding="utf-8")
    assert 'revision = "civicclerk_0012_action_actor"' in text
    assert 'down_revision = "civicclerk_0011_data_model"' in text
    assert '"actor"' in text and '"action_items"' in text
