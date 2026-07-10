# CivicMeetings Persistence Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the four in-memory legal-record stores (motions/votes/action items, minutes drafts, public archive records, public comments) onto database-backed repositories so the legal record survives an API restart whenever the DB env vars are set, while preserving every existing HTTP response shape, immutability 409, and validation behavior byte-for-byte.

**Architecture:** Each workflow module (`civicclerk/motion_vote.py`, `civicclerk/minutes.py`, `civicclerk/public_archive.py`) gains a `*Repository` class alongside its existing in-memory store, following `AgendaIntakeRepository` (`civicclerk/agenda_intake.py:91-252`) exactly: module-level `sa.MetaData()` mirror tables in the `civicclerk` schema, `schema_translate_map={"civicclerk": None}` on SQLite, `CREATE SCHEMA IF NOT EXISTS civicclerk` + `metadata.create_all()` on Postgres, one `engine.begin()` block per operation, and an `AuditHashChain` recording every write (hash stored in the existing `immutable_hash` columns; NOT added to response payloads). The mirror tables target the EXISTING canonical tables from `civicclerk/models.py` (`motions` L90-107, `votes` L109-124, `action_items` L195-208, `minutes` L161-178, `public_comments` L126-143) plus one NEW `public_meeting_records` table. Three new alembic migrations (0012/0013/0014) extend the chain after `civicclerk_0011_data_model`. `main.py` lazy getters (pattern: `_get_meeting_store` at `civicclerk/main.py:3388-3396`) select the repository when the env var is set and fall back to the module-level in-memory store otherwise. New env vars: `CIVICCLERK_MOTION_VOTE_DB_URL`, `CIVICCLERK_MINUTES_DB_URL`, `CIVICCLERK_PUBLIC_ARCHIVE_DB_URL` (archive records + comments share the last one).

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.x Core (`sa.Table` + `sa.Uuid(as_uuid=False)` for dialect portability), Alembic (manual revision files under `civicclerk/migrations/versions/`, idempotent guards as in `civicclerk_0011_data_model_completion.py`), `civiccore.audit.AuditHashChain`, pytest with `asyncio_mode = "auto"` and httpx `ASGITransport`. All commands run from `C:\CivicSuiteDev\repos\civicclerk`.

---

## Task 1: MotionVoteRepository (motions + votes + action_items)

**Files:**
- Create: `civicclerk/migrations/versions/civicclerk_0012_action_item_actor.py`
- Modify: `civicclerk/motion_vote.py` (add imports, mirror tables, `MotionVoteRepository`, `_uuid_text_or_none`, extend `__all__`; in-memory `MotionVoteStore` at L92-257 stays untouched)
- Test: `tests/test_production_depth_motion_vote_persistence.py` (new)

### Steps

- [ ] **Write the failing restart-survival + behavior tests.** Create `tests/test_production_depth_motion_vote_persistence.py`:

```python
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
```

- [ ] **Run the tests and confirm they fail for the right reason.** Run: `python -m pytest tests/test_production_depth_motion_vote_persistence.py -x -q` — expect `ImportError: cannot import name 'MotionVoteRepository' from 'civicclerk.motion_vote'`.

- [ ] **Create the migration** `civicclerk/migrations/versions/civicclerk_0012_action_item_actor.py` (format mirrors `civicclerk_0010_vendor_sync_cursor.py`):

```python
"""Add actor attribution to action_items for restart-safe capture records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "civicclerk_0012_action_actor"
down_revision = "civicclerk_0011_data_model"
branch_labels = None
depends_on = None

SCHEMA = "civicclerk"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("action_items", schema=SCHEMA)
    }
    if "actor" not in columns:
        op.add_column(
            "action_items",
            sa.Column("actor", sa.String(255), nullable=True),
            schema=SCHEMA,
        )


def downgrade() -> None:
    op.drop_column("action_items", "actor", schema=SCHEMA)
```

- [ ] **Add the canonical column to `civicclerk/models.py`** so the SQLAlchemy contract matches the migration. In the `action_items` table (models.py L195-208), after the `assigned_to` column add:

```python
    sa.Column("actor", sa.String(255), nullable=True),
```

  (Do NOT add new tables to models.py — the milestone-2 canonical-table test enumerates tables, not columns, and `agenda_intake_queue` precedent keeps repository-only tables out of `Base.metadata`. Adding a column is safe; `test_each_canonical_table_has_required_foundation_columns` only checks `id/created_at/updated_at`.)

- [ ] **Implement `MotionVoteRepository` in `civicclerk/motion_vote.py`.** Add imports at the top of the file:

```python
from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiccore.audit import AuditActor, AuditHashChain, AuditSubject
```

  Add mirror tables (module level, after the dataclasses, before `MotionVoteStore`). Column names/types mirror `civicclerk/models.py` `motions`/`votes`/`action_items` exactly; `sa.Uuid(as_uuid=False)` keeps string ids portable across SQLite and the Postgres `uuid` columns; mirror tables declare no FKs (matching `meeting_body.py` L15-25 precedent) because Alembic owns the real constraints on Postgres and `create_all(checkfirst)` no-ops there:

```python
metadata = sa.MetaData()

motions_table = sa.Table(
    "motions",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("agenda_item_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("seconded_by", sa.String(255), nullable=True),
    sa.Column("captured_by", sa.String(255), nullable=True),
    sa.Column("correction_of_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("correction_reason", sa.Text(), nullable=True),
    sa.Column("immutable_hash", sa.String(128), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

votes_table = sa.Table(
    "votes",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("motion_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("voter_name", sa.String(255), nullable=False),
    sa.Column("vote", sa.String(50), nullable=False),
    sa.Column("actor", sa.String(255), nullable=True),
    sa.Column("correction_of_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("correction_reason", sa.Text(), nullable=True),
    sa.Column("immutable_hash", sa.String(128), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

action_items_table = sa.Table(
    "action_items",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("description", sa.Text(), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("assigned_to", sa.String(255), nullable=True),
    sa.Column("source_motion_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("actor", sa.String(255), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)
```

  Add the repository class after `MotionVoteStore`:

```python
class MotionVoteRepository:
    """SQLAlchemy-backed motion, vote, and action-item capture store.

    Persists the legal record onto the canonical civicclerk.motions, votes,
    and action_items tables so captured outcomes survive an API restart.
    Wiring mirrors AgendaIntakeRepository: SQLite local demos translate the
    civicclerk schema away; PostgreSQL keeps it. Corrections stay append-only
    insert operations; rows are never updated or deleted.
    """

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
        metadata.create_all(self.engine)
        self.audit_chain = AuditHashChain()

    def capture_motion(
        self,
        *,
        meeting_id: str,
        text: str,
        actor: str,
        agenda_item_id: str | None = None,
        seconded_by: str | None = None,
        correction_of_id: str | None = None,
        correction_reason: str | None = None,
    ) -> MotionRecord:
        now = datetime.now(UTC)
        motion_id = str(uuid4())
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="clerk"),
            action="motion_vote.motion_captured",
            subject=AuditSubject(subject_id=motion_id, subject_type="motion"),
            source_module="civicclerk",
            metadata={
                "meeting_id": meeting_id,
                "correction_of_id": correction_of_id,
            },
        )
        values = {
            "id": motion_id,
            "meeting_id": meeting_id,
            "agenda_item_id": _uuid_text_or_none(agenda_item_id),
            "text": text,
            "seconded_by": _normalize_optional_text(seconded_by),
            "captured_by": actor,
            "correction_of_id": correction_of_id,
            "correction_reason": correction_reason,
            "immutable_hash": event.current_hash or "",
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(motions_table.insert().values(**values))
        return self.get_motion(motion_id) or _motion_row_to_record(values)

    def get_motion(self, motion_id: str) -> MotionRecord | None:
        parsed = _uuid_text_or_none(motion_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(motions_table).where(motions_table.c.id == parsed)
            ).mappings().first()
        return _motion_row_to_record(row) if row is not None else None

    def list_motions(self, meeting_id: str) -> list[MotionRecord]:
        parsed = _uuid_text_or_none(meeting_id)
        if parsed is None:
            return []
        statement = (
            sa.select(motions_table)
            .where(motions_table.c.meeting_id == parsed)
            .order_by(motions_table.c.created_at.asc(), motions_table.c.id.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_motion_row_to_record(row) for row in rows]

    def correct_motion(
        self,
        *,
        original_motion_id: str,
        text: str,
        actor: str,
        reason: str,
    ) -> MotionRecord | None:
        original = self.get_motion(original_motion_id)
        if original is None:
            return None
        return self.capture_motion(
            meeting_id=original.meeting_id,
            agenda_item_id=original.agenda_item_id,
            text=text,
            actor=actor,
            seconded_by=original.seconded_by,
            correction_of_id=original.id,
            correction_reason=reason,
        )

    def capture_vote(
        self,
        *,
        motion_id: str,
        voter_name: str,
        vote: str,
        actor: str,
        correction_of_id: str | None = None,
        correction_reason: str | None = None,
    ) -> VoteRecord:
        now = datetime.now(UTC)
        vote_id = str(uuid4())
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="clerk"),
            action="motion_vote.vote_captured",
            subject=AuditSubject(subject_id=vote_id, subject_type="vote"),
            source_module="civicclerk",
            metadata={
                "motion_id": motion_id,
                "correction_of_id": correction_of_id,
            },
        )
        values = {
            "id": vote_id,
            "motion_id": motion_id,
            "voter_name": voter_name,
            "vote": vote.strip().lower(),
            "actor": actor,
            "correction_of_id": correction_of_id,
            "correction_reason": correction_reason,
            "immutable_hash": event.current_hash or "",
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(votes_table.insert().values(**values))
        return self.get_vote(vote_id) or _vote_row_to_record(values)

    def get_vote(self, vote_id: str) -> VoteRecord | None:
        parsed = _uuid_text_or_none(vote_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(votes_table).where(votes_table.c.id == parsed)
            ).mappings().first()
        return _vote_row_to_record(row) if row is not None else None

    def list_votes(self, motion_id: str) -> list[VoteRecord]:
        parsed = _uuid_text_or_none(motion_id)
        if parsed is None:
            return []
        statement = (
            sa.select(votes_table)
            .where(votes_table.c.motion_id == parsed)
            .order_by(votes_table.c.created_at.asc(), votes_table.c.id.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_vote_row_to_record(row) for row in rows]

    def correct_vote(
        self,
        *,
        original_vote_id: str,
        vote: str,
        actor: str,
        reason: str,
    ) -> VoteRecord | None:
        original = self.get_vote(original_vote_id)
        if original is None:
            return None
        return self.capture_vote(
            motion_id=original.motion_id,
            voter_name=original.voter_name,
            vote=vote,
            actor=actor,
            correction_of_id=original.id,
            correction_reason=reason,
        )

    def create_action_item(
        self,
        *,
        meeting_id: str,
        description: str,
        actor: str,
        assigned_to: str | None = None,
        source_motion_id: str | None = None,
    ) -> ActionItemRecord:
        now = datetime.now(UTC)
        action_item_id = str(uuid4())
        event = self.audit_chain.record_event(
            actor=AuditActor(actor_id=actor, actor_type="clerk"),
            action="motion_vote.action_item_created",
            subject=AuditSubject(subject_id=action_item_id, subject_type="action_item"),
            source_module="civicclerk",
            metadata={
                "meeting_id": meeting_id,
                "source_motion_id": source_motion_id,
            },
        )
        del event  # action_items has no immutable_hash column; chain still records the write.
        values = {
            "id": action_item_id,
            "meeting_id": meeting_id,
            "description": description,
            "status": "OPEN",
            "assigned_to": assigned_to,
            "source_motion_id": source_motion_id,
            "actor": actor,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(action_items_table.insert().values(**values))
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(action_items_table).where(action_items_table.c.id == action_item_id)
            ).mappings().first()
        return _action_item_row_to_record(row if row is not None else values)

    def list_action_items(self, meeting_id: str) -> list[ActionItemRecord]:
        parsed = _uuid_text_or_none(meeting_id)
        if parsed is None:
            return []
        statement = (
            sa.select(action_items_table)
            .where(action_items_table.c.meeting_id == parsed)
            .order_by(action_items_table.c.created_at.asc(), action_items_table.c.id.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_action_item_row_to_record(row) for row in rows]

    def list_recent_outcomes(self, *, limit: int = 5) -> list[MeetingOutcomeSummary]:
        """Return recent motion-centered outcome summaries for the staff dashboard."""

        summaries: list[MeetingOutcomeSummary] = []
        with self.engine.begin() as connection:
            motion_rows = connection.execute(
                sa.select(motions_table)
                .order_by(motions_table.c.created_at.desc(), motions_table.c.id.desc())
                .limit(limit)
            ).mappings().all()
            for row in motion_rows:
                vote_count = connection.execute(
                    sa.select(sa.func.count())
                    .select_from(votes_table)
                    .where(votes_table.c.motion_id == row["id"])
                ).scalar_one()
                action_item_count = connection.execute(
                    sa.select(sa.func.count())
                    .select_from(action_items_table)
                    .where(action_items_table.c.source_motion_id == row["id"])
                ).scalar_one()
                record = _motion_row_to_record(row)
                summaries.append(
                    MeetingOutcomeSummary(
                        meeting_id=record.meeting_id,
                        motion_id=record.id,
                        text=record.text,
                        actor=record.actor,
                        status="APPENDED" if record.correction_of_id else "CAPTURED",
                        vote_count=int(vote_count),
                        action_item_count=int(action_item_count),
                    )
                )
        return summaries
```

  Add the row converters and helper after `_normalize_optional_text` (which already exists at `civicclerk/motion_vote.py:260-264` — reuse it, do NOT redefine it):

```python
def _uuid_text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (AttributeError, TypeError, ValueError):
        return None


def _motion_row_to_record(row) -> MotionRecord:
    data = dict(row)
    return MotionRecord(
        id=str(data["id"]),
        meeting_id=str(data["meeting_id"]),
        agenda_item_id=str(data["agenda_item_id"]) if data.get("agenda_item_id") else None,
        text=data["text"],
        actor=data.get("captured_by") or "",
        seconded_by=data.get("seconded_by"),
        correction_of_id=str(data["correction_of_id"]) if data.get("correction_of_id") else None,
        correction_reason=data.get("correction_reason"),
    )


def _vote_row_to_record(row) -> VoteRecord:
    data = dict(row)
    return VoteRecord(
        id=str(data["id"]),
        motion_id=str(data["motion_id"]),
        voter_name=data["voter_name"],
        vote=data["vote"],
        actor=data.get("actor") or "",
        correction_of_id=str(data["correction_of_id"]) if data.get("correction_of_id") else None,
        correction_reason=data.get("correction_reason"),
    )


def _action_item_row_to_record(row) -> ActionItemRecord:
    data = dict(row)
    return ActionItemRecord(
        id=str(data["id"]),
        meeting_id=str(data["meeting_id"]),
        description=data["description"],
        actor=data.get("actor") or "",
        assigned_to=data.get("assigned_to"),
        source_motion_id=str(data["source_motion_id"]) if data.get("source_motion_id") else None,
        status=data.get("status") or "OPEN",
    )
```

  The `captured` flag never hits the database: `MotionRecord.captured` / `VoteRecord.captured` default to `True` and the row converters never override it, so `public_dict()` always emits `"captured": True` — exact frontend contract `{id, meeting_id, agenda_item_id, text, actor, seconded_by, correction_of_id, correction_reason, captured}` preserved. Extend `__all__`:

```python
__all__ = [
    "ActionItemRecord",
    "MeetingOutcomeSummary",
    "MotionRecord",
    "MotionVoteRepository",
    "MotionVoteStore",
    "VoteRecord",
]
```

- [ ] **Run the tests and confirm they pass.** Run: `python -m pytest tests/test_production_depth_motion_vote_persistence.py -x -q` — expect `4 passed`.

- [ ] **Run the existing milestone 6 suite to prove no regression.** Run: `python -m pytest tests/test_milestone_6_motion_vote_action_capture.py tests/test_milestone_2_schema_and_migrations.py -q` — expect all passed (no env var set, in-memory path untouched).

- [ ] **Commit.** Run: `git add civicclerk/motion_vote.py civicclerk/models.py civicclerk/migrations/versions/civicclerk_0012_action_item_actor.py tests/test_production_depth_motion_vote_persistence.py && git commit -s -m "feat(persistence): add MotionVoteRepository with append-only corrections"`

---

## Task 2: MinutesDraftRepository (minutes table)

**Files:**
- Create: `civicclerk/migrations/versions/civicclerk_0013_minutes_model_posted.py`
- Modify: `civicclerk/minutes.py` (add imports, mirror table, `MinutesDraftRepository`, row converter, extend `__all__`; `MinutesDraftStore` at L65-126 stays untouched), `civicclerk/models.py` (add `model` and `posted_at` columns to `minutes`)
- Test: `tests/test_production_depth_minutes_persistence.py` (new)

**Provenance storage decision (documented):** `MinutesProvenance` decomposes into existing `minutes` columns wherever they already exist — `prompt_version` and `human_approver` columns shipped in migration 0011. `provenance.model` gets a NEW `model` column (String(255), nullable) rather than a JSON blob, because the table already decomposes the other provenance fields into typed columns and a mixed column/JSON split would be the worst of both. `provenance.data_sources` is DERIVED on read from the `source_materials` JSON (`[sm["source_id"] for sm in ...]`) — it is never stored separately, matching how `MinutesDraftStore.create_draft` derives it (`civicclerk/minutes.py:96`). `adopted` is derived as `adopted_at IS NOT NULL`; `posted` is derived from the NEW `posted_at` column (DateTime, nullable). The NOT NULL `body` column is populated with `"\n".join(sentence.text ...)` so the canonical contract from migration 0001 stays satisfied.

### Steps

- [ ] **Write the failing tests.** Create `tests/test_production_depth_minutes_persistence.py`:

```python
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from civicclerk.minutes import (
    MinutesDraftRepository,
    MinutesSentence,
    MinutesValidationError,
    SourceMaterial,
)

ROOT = Path(__file__).resolve().parents[1]


def _source() -> SourceMaterial:
    return SourceMaterial(
        source_id="motion-sidewalk-contract",
        label="Captured motion and roll-call vote",
        text="Council approved the sidewalk repair contract by a 3-1 vote.",
    )


def test_minutes_drafts_persist_across_repository_instances(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'minutes.db'}"
    meeting_id = str(uuid4())

    first = MinutesDraftRepository(db_url=db_url)
    draft = first.create_draft(
        meeting_id=meeting_id,
        model="ollama/gemma4",
        prompt_version="minutes_draft@0.1.0",
        human_approver="clerk@example.gov",
        source_materials=[_source()],
        sentences=[
            MinutesSentence(
                text="Council approved the sidewalk repair contract by a 3-1 vote.",
                citations=("motion-sidewalk-contract",),
            )
        ],
    )
    assert hasattr(draft, "public_dict"), getattr(draft, "message", draft)

    second = MinutesDraftRepository(db_url=db_url)
    drafts = second.list_drafts(meeting_id)

    assert [d.id for d in drafts] == [draft.id]
    assert drafts[0].public_dict() == {
        "id": draft.id,
        "meeting_id": meeting_id,
        "status": "DRAFT",
        "sentences": [
            {
                "text": "Council approved the sidewalk repair contract by a 3-1 vote.",
                "citations": ["motion-sidewalk-contract"],
            }
        ],
        "source_materials": [
            {
                "source_id": "motion-sidewalk-contract",
                "label": "Captured motion and roll-call vote",
                "text": "Council approved the sidewalk repair contract by a 3-1 vote.",
            }
        ],
        "provenance": {
            "model": "ollama/gemma4",
            "prompt_version": "minutes_draft@0.1.0",
            "data_sources": ["motion-sidewalk-contract"],
            "human_approver": "clerk@example.gov",
        },
        "adopted": False,
        "posted": False,
    }
    assert second.get_draft(draft.id) is not None
    assert second.get_draft("not-a-uuid") is None
    assert [d.id for d in second.list_recent(limit=1)] == [draft.id]


def test_repository_enforces_prompt_library_and_citation_gates(tmp_path) -> None:
    repo = MinutesDraftRepository(db_url=f"sqlite:///{tmp_path / 'gates.db'}")
    bad_prompt = repo.create_draft(
        meeting_id=str(uuid4()),
        model="ollama/gemma4",
        prompt_version="not-a-known-version",
        human_approver="clerk@example.gov",
        source_materials=[_source()],
        sentences=[
            MinutesSentence(text="Cited sentence.", citations=("motion-sidewalk-contract",))
        ],
    )
    uncited = repo.create_draft(
        meeting_id=str(uuid4()),
        model="ollama/gemma4",
        prompt_version="minutes_draft@0.1.0",
        human_approver="clerk@example.gov",
        source_materials=[_source()],
        sentences=[MinutesSentence(text="No citation here.", citations=())],
    )

    assert isinstance(bad_prompt, MinutesValidationError)
    assert "prompt library" in bad_prompt.message.lower() or "prompt version" in bad_prompt.fix.lower()
    assert isinstance(uncited, MinutesValidationError)
    assert "citation" in uncited.message.lower()


def test_migration_0013_adds_model_and_posted_at_and_extends_chain() -> None:
    path = (
        ROOT
        / "civicclerk"
        / "migrations"
        / "versions"
        / "civicclerk_0013_minutes_model_posted.py"
    )
    assert path.exists(), "Missing migration: civicclerk_0013_minutes_model_posted.py"
    text = path.read_text(encoding="utf-8")
    assert 'revision = "civicclerk_0013_minutes_model"' in text
    assert 'down_revision = "civicclerk_0012_action_actor"' in text
    assert '"model"' in text and '"posted_at"' in text and '"minutes"' in text
```

- [ ] **Run the tests and confirm they fail for the right reason.** Run: `python -m pytest tests/test_production_depth_minutes_persistence.py -x -q` — expect `ImportError: cannot import name 'MinutesDraftRepository' from 'civicclerk.minutes'`.

- [ ] **Create the migration** `civicclerk/migrations/versions/civicclerk_0013_minutes_model_posted.py`:

```python
"""Add provenance model and public posting timestamp to minutes."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "civicclerk_0013_minutes_model"
down_revision = "civicclerk_0012_action_actor"
branch_labels = None
depends_on = None

SCHEMA = "civicclerk"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("minutes", schema=SCHEMA)
    }
    if "model" not in columns:
        op.add_column(
            "minutes",
            sa.Column("model", sa.String(255), nullable=True),
            schema=SCHEMA,
        )
    if "posted_at" not in columns:
        op.add_column(
            "minutes",
            sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
            schema=SCHEMA,
        )


def downgrade() -> None:
    op.drop_column("minutes", "posted_at", schema=SCHEMA)
    op.drop_column("minutes", "model", schema=SCHEMA)
```

- [ ] **Add the canonical columns to `civicclerk/models.py`** in the `minutes` table (L161-178), after `human_approver`:

```python
    sa.Column("model", sa.String(255), nullable=True),
```

  and after `adopted_at`:

```python
    sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
```

- [ ] **Implement `MinutesDraftRepository` in `civicclerk/minutes.py`.** Add imports:

```python
from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiccore.audit import AuditActor, AuditHashChain, AuditSubject
```

  Add the mirror table (module level, after `MinutesValidationError`):

```python
metadata = sa.MetaData()

minutes_table = sa.Table(
    "minutes",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("body", sa.Text(), nullable=False),
    sa.Column("source_materials", sa.JSON(), nullable=True),
    sa.Column("sentence_citations", sa.JSON(), nullable=True),
    sa.Column("prompt_version", sa.String(120), nullable=True),
    sa.Column("human_approver", sa.String(255), nullable=True),
    sa.Column("model", sa.String(255), nullable=True),
    sa.Column("adopted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("signed_by", sa.String(255), nullable=True),
    sa.Column("document_ref", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)
```

  Add the repository class after `MinutesDraftStore`:

```python
class MinutesDraftRepository:
    """SQLAlchemy-backed minutes draft store on the canonical minutes table.

    Sentences persist to the sentence_citations JSON column, source materials
    to the source_materials JSON column, and provenance decomposes into the
    model / prompt_version / human_approver columns. data_sources is derived
    from source_materials on read; adopted/posted derive from adopted_at /
    posted_at being non-NULL. The NOT NULL body column stores the joined
    sentence text so the canonical schema contract stays satisfied.
    """

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
        metadata.create_all(self.engine)
        self.audit_chain = AuditHashChain()

    def create_draft(
        self,
        *,
        meeting_id: str,
        model: str,
        prompt_version: str,
        human_approver: str,
        source_materials: list[SourceMaterial],
        sentences: list[MinutesSentence],
    ) -> MinutesDraft | MinutesValidationError:
        if not is_known_prompt_version(prompt_version):
            expected = expected_prompt_version_hint()
            return MinutesValidationError(
                message="Minutes drafts must use a prompt version from the CivicMeetings YAML prompt library.",
                fix=f"Use prompt_version '{expected}' or another version returned by the prompt library.",
            )

        validation_error = validate_minutes_draft(
            source_materials=source_materials,
            sentences=sentences,
        )
        if validation_error is not None:
            return validation_error

        now = datetime.now(UTC)
        draft_id = str(uuid4())
        self.audit_chain.record_event(
            actor=AuditActor(actor_id=human_approver, actor_type="clerk"),
            action="minutes.draft_created",
            subject=AuditSubject(subject_id=draft_id, subject_type="minutes_draft"),
            source_module="civicclerk",
            metadata={
                "meeting_id": meeting_id,
                "sentence_count": len(sentences),
            },
        )
        values = {
            "id": draft_id,
            "meeting_id": meeting_id,
            "status": "DRAFT",
            "body": "\n".join(sentence.text for sentence in sentences),
            "source_materials": [source.public_dict() for source in source_materials],
            "sentence_citations": [sentence.public_dict() for sentence in sentences],
            "prompt_version": prompt_version,
            "human_approver": human_approver,
            "model": model,
            "adopted_at": None,
            "posted_at": None,
            "signed_by": None,
            "document_ref": None,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(minutes_table.insert().values(**values))
        return self.get_draft(draft_id) or _minutes_row_to_draft(values)

    def get_draft(self, draft_id: str) -> MinutesDraft | None:
        parsed = _minutes_uuid_text_or_none(draft_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(minutes_table).where(minutes_table.c.id == parsed)
            ).mappings().first()
        return _minutes_row_to_draft(row) if row is not None else None

    def list_drafts(self, meeting_id: str) -> list[MinutesDraft]:
        parsed = _minutes_uuid_text_or_none(meeting_id)
        if parsed is None:
            return []
        statement = (
            sa.select(minutes_table)
            .where(minutes_table.c.meeting_id == parsed)
            .order_by(minutes_table.c.created_at.asc(), minutes_table.c.id.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_minutes_row_to_draft(row) for row in rows]

    def list_recent(self, *, limit: int = 5) -> list[MinutesDraft]:
        """Return recent citation-gated drafts for the staff dashboard."""

        statement = (
            sa.select(minutes_table)
            .order_by(minutes_table.c.created_at.desc(), minutes_table.c.id.desc())
            .limit(limit)
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_minutes_row_to_draft(row) for row in rows]
```

  Add converters after `validate_minutes_draft`:

```python
def _minutes_uuid_text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (AttributeError, TypeError, ValueError):
        return None


def _minutes_row_to_draft(row) -> MinutesDraft:
    data = dict(row)
    source_materials = tuple(
        SourceMaterial(
            source_id=source["source_id"],
            label=source["label"],
            text=source["text"],
        )
        for source in (data.get("source_materials") or [])
    )
    sentences = tuple(
        MinutesSentence(
            text=sentence["text"],
            citations=tuple(sentence["citations"]),
        )
        for sentence in (data.get("sentence_citations") or [])
    )
    return MinutesDraft(
        id=str(data["id"]),
        meeting_id=str(data["meeting_id"]),
        status=data["status"],
        sentences=sentences,
        source_materials=source_materials,
        provenance=MinutesProvenance(
            model=data.get("model") or "",
            prompt_version=data.get("prompt_version") or "",
            data_sources=tuple(source.source_id for source in source_materials),
            human_approver=data.get("human_approver") or "",
        ),
        adopted=data.get("adopted_at") is not None,
        posted=data.get("posted_at") is not None,
    )
```

  Extend `__all__`:

```python
__all__ = [
    "MinutesDraft",
    "MinutesDraftRepository",
    "MinutesDraftStore",
    "MinutesProvenance",
    "MinutesSentence",
    "MinutesValidationError",
    "SourceMaterial",
    "validate_minutes_draft",
]
```

- [ ] **Run the tests and confirm they pass.** Run: `python -m pytest tests/test_production_depth_minutes_persistence.py -x -q` — expect `3 passed`.

- [ ] **Run the milestone 7 suite to prove no regression.** Run: `python -m pytest tests/test_milestone_7_minutes_citations.py tests/test_milestone_2_schema_and_migrations.py -q` — expect all passed.

- [ ] **Commit.** Run: `git add civicclerk/minutes.py civicclerk/models.py civicclerk/migrations/versions/civicclerk_0013_minutes_model_posted.py tests/test_production_depth_minutes_persistence.py && git commit -s -m "feat(persistence): persist minutes drafts onto canonical minutes table"`

---

## Task 3: PublicArchiveRepository + PublicCommentRepository

**Files:**
- Create: `civicclerk/migrations/versions/civicclerk_0014_public_meeting_records.py`
- Modify: `civicclerk/public_archive.py` (add imports, two mirror tables, `PublicArchiveRepository`, `PublicCommentRepository`, converters, extend `__all__`; in-memory stores at L80-183 stay untouched)
- Test: `tests/test_production_depth_public_archive_persistence.py` (new)

The NEW `public_meeting_records` table column-for-column matches the `PublicMeetingRecord` dataclass fields (`civicclerk/public_archive.py:20-37`), including the three derived download URLs (stored so a row round-trips without recomputation). `PublicCommentRepository` writes onto the EXISTING `public_comments` table (`civicclerk/models.py:126-143`): the API's `comment` field maps to the `body` column, `visibility` defaults to `"public"` (comments are only accepted against public records — gating preserved), `status` defaults to `"RECEIVED"`, and the comment's `meeting_id` NOT NULL column is filled from the parent public record's `meeting_id`. The table is NOT added to `civicclerk/models.py` — `test_canonical_table_models_exist_and_no_tables_are_missing_or_extra` pins the canonical table set, and `agenda_intake_queue`/`vendor_sync_*` set the precedent that repository-owned tables live in their module plus a migration.

### Steps

- [ ] **Write the failing tests.** Create `tests/test_production_depth_public_archive_persistence.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from civicclerk.public_archive import (
    PublicArchiveRepository,
    PublicCommentRepository,
)

ROOT = Path(__file__).resolve().parents[1]


def test_public_records_persist_across_repository_instances(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'archive.db'}"
    meeting_id = str(uuid4())

    first = PublicArchiveRepository(db_url=db_url)
    record = first.publish(
        meeting_id=meeting_id,
        title="Brookfield City Council Prior Meeting",
        visibility="  PUBLIC ",
        posted_agenda="Agenda included sidewalk repair contract award.",
        posted_packet="Packet included Public Works memo.",
        approved_minutes="Approved minutes record the contract vote.",
        public_comment_enabled=True,
        plain_language_summary="  Council approved the sidewalk contract.  ",
        minutes_adopted_at="2026-06-01T19:00:00+00:00",
        minutes_signed_by="clerk@example.gov",
    )

    second = PublicArchiveRepository(db_url=db_url)
    calendar = second.public_calendar()

    assert [r.id for r in calendar] == [record.id]
    assert calendar[0].public_dict() == {
        "id": record.id,
        "meeting_id": meeting_id,
        "title": "Brookfield City Council Prior Meeting",
        "posted_agenda": "Agenda included sidewalk repair contract award.",
        "posted_packet": "Packet included Public Works memo.",
        "approved_minutes": "Approved minutes record the contract vote.",
        "public_comment_enabled": True,
        "plain_language_summary": "Council approved the sidewalk contract.",
        "agenda_download_url": f"/public/meetings/{record.id}/agenda.txt",
        "packet_download_url": f"/public/meetings/{record.id}/packet.txt",
        "minutes_download_url": f"/public/meetings/{record.id}/minutes.txt",
        "minutes_adopted_at": "2026-06-01T19:00:00+00:00",
        "minutes_signed_by": "clerk@example.gov",
    }
    assert second.public_detail(record.id) is not None
    assert second.public_detail(str(uuid4())) is None
    assert [r.id for r in second.search(query="sidewalk")] == [record.id]
    assert second.search(query="zzz-no-match") == []


def test_closed_session_records_hidden_from_public_surfaces(tmp_path) -> None:
    repo = PublicArchiveRepository(db_url=f"sqlite:///{tmp_path / 'closed.db'}")
    closed = repo.publish(
        meeting_id=str(uuid4()),
        title="Closed Session - Litigation",
        visibility="closed_session",
        posted_agenda="Closed session agenda.",
        posted_packet="Closed session packet.",
        approved_minutes="Closed session minutes.",
        closed_session_notes="Litigation strategy notes.",
    )

    assert repo.public_calendar() == []
    assert repo.public_detail(closed.id) is None
    assert repo.search(query="litigation") == []
    found = repo.search(query="litigation", include_closed=True)
    assert [r.id for r in found] == [closed.id]
    payload = found[0].public_dict(include_closed=True)
    assert payload["visibility"] == "closed_session"
    assert payload["closed_session_notes"] == "Litigation strategy notes."


def test_public_comments_persist_and_respect_intake_gating(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'comments.db'}"
    archive = PublicArchiveRepository(db_url=db_url)
    open_record = archive.publish(
        meeting_id=str(uuid4()),
        title="Open Comment Meeting",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
        public_comment_enabled=True,
    )
    closed_record = archive.publish(
        meeting_id=str(uuid4()),
        title="No Comment Meeting",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
        public_comment_enabled=False,
    )
    submitted_at = datetime.now(UTC).isoformat()

    first = PublicCommentRepository(db_url=db_url)
    comment = first.submit(
        public_record=open_record,
        commenter_name="  Resident Lee  ",
        comment="  Please add a crosswalk at Oak Street.  ",
        submitted_at=submitted_at,
    )
    rejected = first.submit(
        public_record=closed_record,
        commenter_name="Resident Lee",
        comment="This should be rejected.",
        submitted_at=submitted_at,
    )

    assert comment is not None
    assert rejected is None

    second = PublicCommentRepository(db_url=db_url)
    listed = second.list_for_record(open_record.id)

    assert [c.id for c in listed] == [comment.id]
    assert listed[0].public_dict() == {
        "id": comment.id,
        "public_record_id": open_record.id,
        "commenter_name": "Resident Lee",
        "comment": "Please add a crosswalk at Oak Street.",
        "submitted_at": submitted_at,
        "status": "RECEIVED",
    }
    assert [c.id for c in second.list_all()] == [comment.id]


def test_migration_0014_creates_public_meeting_records_and_extends_chain() -> None:
    path = (
        ROOT
        / "civicclerk"
        / "migrations"
        / "versions"
        / "civicclerk_0014_public_meeting_records.py"
    )
    assert path.exists(), "Missing migration: civicclerk_0014_public_meeting_records.py"
    text = path.read_text(encoding="utf-8")
    assert 'revision = "civicclerk_0014_public_records"' in text
    assert 'down_revision = "civicclerk_0013_minutes_model"' in text
    assert '"public_meeting_records"' in text
```

- [ ] **Run the tests and confirm they fail for the right reason.** Run: `python -m pytest tests/test_production_depth_public_archive_persistence.py -x -q` — expect `ImportError: cannot import name 'PublicArchiveRepository' from 'civicclerk.public_archive'`.

- [ ] **Create the migration** `civicclerk/migrations/versions/civicclerk_0014_public_meeting_records.py` (uses the repo's `idempotent_create_table` guard from `civicclerk/migrations/guards.py`, same as the agenda-intake table migration):

```python
"""Create public_meeting_records for the persisted public archive."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civicclerk.migrations.guards import idempotent_create_table


revision = "civicclerk_0014_public_records"
down_revision = "civicclerk_0013_minutes_model"
branch_labels = None
depends_on = None

SCHEMA = "civicclerk"


def upgrade() -> None:
    idempotent_create_table(
        "public_meeting_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("visibility", sa.String(80), nullable=False),
        sa.Column("posted_agenda", sa.Text(), nullable=False),
        sa.Column("posted_packet", sa.Text(), nullable=False),
        sa.Column("approved_minutes", sa.Text(), nullable=False),
        sa.Column("public_comment_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("plain_language_summary", sa.Text(), nullable=True),
        sa.Column("agenda_download_url", sa.Text(), nullable=True),
        sa.Column("packet_download_url", sa.Text(), nullable=True),
        sa.Column("minutes_download_url", sa.Text(), nullable=True),
        sa.Column("minutes_adopted_at", sa.String(120), nullable=True),
        sa.Column("minutes_signed_by", sa.String(255), nullable=True),
        sa.Column("closed_session_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("public_meeting_records", schema=SCHEMA)
```

- [ ] **Implement both repositories in `civicclerk/public_archive.py`.** Add imports:

```python
from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civiccore.audit import AuditActor, AuditHashChain, AuditSubject
```

  Add mirror tables (module level, after `PublicCommentRecord`):

```python
metadata = sa.MetaData()

public_meeting_records_table = sa.Table(
    "public_meeting_records",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("visibility", sa.String(80), nullable=False),
    sa.Column("posted_agenda", sa.Text(), nullable=False),
    sa.Column("posted_packet", sa.Text(), nullable=False),
    sa.Column("approved_minutes", sa.Text(), nullable=False),
    sa.Column("public_comment_enabled", sa.Boolean(), nullable=False),
    sa.Column("plain_language_summary", sa.Text(), nullable=True),
    sa.Column("agenda_download_url", sa.Text(), nullable=True),
    sa.Column("packet_download_url", sa.Text(), nullable=True),
    sa.Column("minutes_download_url", sa.Text(), nullable=True),
    sa.Column("minutes_adopted_at", sa.String(120), nullable=True),
    sa.Column("minutes_signed_by", sa.String(255), nullable=True),
    sa.Column("closed_session_notes", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

public_comments_table = sa.Table(
    "public_comments",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
    sa.Column("meeting_id", sa.Uuid(as_uuid=False), nullable=False),
    sa.Column("agenda_item_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("public_record_id", sa.Uuid(as_uuid=False), nullable=True),
    sa.Column("commenter_name", sa.String(255), nullable=False),
    sa.Column("body", sa.Text(), nullable=False),
    sa.Column("visibility", sa.String(80), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("moderation_notes", sa.Text(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)
```

  Add the repository classes after `PublicCommentStore`:

```python
class PublicArchiveRepository:
    """SQLAlchemy-backed public archive on the public_meeting_records table."""

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
        metadata.create_all(self.engine)
        self.audit_chain = AuditHashChain()

    def publish(
        self,
        *,
        meeting_id: str,
        title: str,
        visibility: str,
        posted_agenda: str,
        posted_packet: str,
        approved_minutes: str,
        public_comment_enabled: bool = False,
        plain_language_summary: str | None = None,
        minutes_adopted_at: str | None = None,
        minutes_signed_by: str | None = None,
        closed_session_notes: str | None = None,
    ) -> PublicMeetingRecord:
        from datetime import UTC

        now = datetime.now(UTC)
        record_id = str(uuid4())
        self.audit_chain.record_event(
            actor=AuditActor(actor_id="civicclerk", actor_type="system"),
            action="public_archive.record_published",
            subject=AuditSubject(subject_id=record_id, subject_type="public_meeting_record"),
            source_module="civicclerk",
            metadata={"meeting_id": meeting_id, "visibility": normalize_visibility(visibility)},
        )
        values = {
            "id": record_id,
            "meeting_id": meeting_id,
            "title": title,
            "visibility": normalize_visibility(visibility),
            "posted_agenda": posted_agenda,
            "posted_packet": posted_packet,
            "approved_minutes": approved_minutes,
            "public_comment_enabled": public_comment_enabled,
            "plain_language_summary": _normalize_optional_text(plain_language_summary),
            "agenda_download_url": f"/public/meetings/{record_id}/agenda.txt",
            "packet_download_url": f"/public/meetings/{record_id}/packet.txt",
            "minutes_download_url": f"/public/meetings/{record_id}/minutes.txt",
            "minutes_adopted_at": _normalize_optional_text(minutes_adopted_at),
            "minutes_signed_by": _normalize_optional_text(minutes_signed_by),
            "closed_session_notes": closed_session_notes,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(public_meeting_records_table.insert().values(**values))
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(public_meeting_records_table).where(
                    public_meeting_records_table.c.id == record_id
                )
            ).mappings().first()
        return _public_record_row_to_record(row if row is not None else values)

    def public_calendar(self) -> list[PublicMeetingRecord]:
        statement = (
            sa.select(public_meeting_records_table)
            .where(public_meeting_records_table.c.visibility == PUBLIC_VISIBILITY)
            .order_by(
                public_meeting_records_table.c.created_at.asc(),
                public_meeting_records_table.c.id.asc(),
            )
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_public_record_row_to_record(row) for row in rows]

    def public_detail(self, record_id: str) -> PublicMeetingRecord | None:
        parsed = _archive_uuid_text_or_none(record_id)
        if parsed is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(public_meeting_records_table).where(
                    public_meeting_records_table.c.id == parsed
                )
            ).mappings().first()
        if row is None:
            return None
        record = _public_record_row_to_record(row)
        if record.visibility != PUBLIC_VISIBILITY:
            return None
        return record

    def search(self, *, query: str, include_closed: bool = False) -> list[PublicMeetingRecord]:
        normalized_query = normalize_search_query(query)
        statement = sa.select(public_meeting_records_table).order_by(
            public_meeting_records_table.c.created_at.asc(),
            public_meeting_records_table.c.id.asc(),
        )
        if not include_closed:
            statement = statement.where(
                public_meeting_records_table.c.visibility == PUBLIC_VISIBILITY
            )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        results: list[PublicMeetingRecord] = []
        for row in rows:
            record = _public_record_row_to_record(row)
            if _record_matches(record, normalized_query, include_closed=include_closed):
                results.append(record)
        return results


class PublicCommentRepository:
    """SQLAlchemy-backed resident comment intake on the public_comments table.

    The API "comment" field maps to the canonical body column; visibility
    defaults to public because comments are only accepted against public
    records with comment intake enabled (same gating as PublicCommentStore).
    """

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
        metadata.create_all(self.engine)
        self.audit_chain = AuditHashChain()

    def submit(
        self,
        *,
        public_record: PublicMeetingRecord,
        commenter_name: str,
        comment: str,
        submitted_at: str,
    ) -> PublicCommentRecord | None:
        if public_record.visibility != PUBLIC_VISIBILITY or not public_record.public_comment_enabled:
            return None
        from datetime import UTC

        now = datetime.now(UTC)
        comment_id = str(uuid4())
        self.audit_chain.record_event(
            actor=AuditActor(actor_id=commenter_name.strip(), actor_type="resident"),
            action="public_archive.comment_received",
            subject=AuditSubject(subject_id=comment_id, subject_type="public_comment"),
            source_module="civicclerk",
            metadata={"public_record_id": public_record.id},
        )
        values = {
            "id": comment_id,
            "meeting_id": public_record.meeting_id,
            "agenda_item_id": None,
            "public_record_id": public_record.id,
            "commenter_name": commenter_name.strip(),
            "body": comment.strip(),
            "visibility": PUBLIC_VISIBILITY,
            "status": "RECEIVED",
            "submitted_at": datetime.fromisoformat(submitted_at),
            "moderation_notes": None,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(public_comments_table.insert().values(**values))
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(public_comments_table).where(public_comments_table.c.id == comment_id)
            ).mappings().first()
        return _comment_row_to_record(row if row is not None else values)

    def list_for_record(self, public_record_id: str) -> list[PublicCommentRecord]:
        parsed = _archive_uuid_text_or_none(public_record_id)
        if parsed is None:
            return []
        statement = (
            sa.select(public_comments_table)
            .where(public_comments_table.c.public_record_id == parsed)
            .order_by(public_comments_table.c.created_at.asc(), public_comments_table.c.id.asc())
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_comment_row_to_record(row) for row in rows]

    def list_all(self) -> list[PublicCommentRecord]:
        statement = sa.select(public_comments_table).order_by(
            public_comments_table.c.created_at.asc(), public_comments_table.c.id.asc()
        )
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_comment_row_to_record(row) for row in rows]
```

  Add converters after `_record_matches`:

```python
def _archive_uuid_text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (AttributeError, TypeError, ValueError):
        return None


def _public_record_row_to_record(row) -> PublicMeetingRecord:
    data = dict(row)
    return PublicMeetingRecord(
        id=str(data["id"]),
        meeting_id=str(data["meeting_id"]),
        title=data["title"],
        visibility=data["visibility"],
        posted_agenda=data["posted_agenda"],
        posted_packet=data["posted_packet"],
        approved_minutes=data["approved_minutes"],
        public_comment_enabled=bool(data["public_comment_enabled"]),
        plain_language_summary=data.get("plain_language_summary"),
        agenda_download_url=data.get("agenda_download_url"),
        packet_download_url=data.get("packet_download_url"),
        minutes_download_url=data.get("minutes_download_url"),
        minutes_adopted_at=data.get("minutes_adopted_at"),
        minutes_signed_by=data.get("minutes_signed_by"),
        closed_session_notes=data.get("closed_session_notes"),
    )


def _comment_row_to_record(row) -> PublicCommentRecord:
    data = dict(row)
    submitted = data.get("submitted_at")
    if isinstance(submitted, datetime):
        submitted_text = submitted.isoformat()
    else:
        submitted_text = str(submitted) if submitted else ""
    return PublicCommentRecord(
        id=str(data["id"]),
        public_record_id=str(data["public_record_id"]) if data.get("public_record_id") else "",
        commenter_name=data["commenter_name"],
        comment=data["body"],
        submitted_at=submitted_text,
        status=data.get("status") or "RECEIVED",
    )
```

  Extend `__all__`:

```python
__all__ = [
    "CLOSED_SESSION_VISIBILITY",
    "PERMITTED_CLOSED_SESSION_ROLES",
    "PUBLIC_VISIBILITY",
    "PublicArchiveRepository",
    "PublicArchiveStore",
    "PublicCommentRecord",
    "PublicCommentRepository",
    "PublicCommentStore",
    "PublicMeetingRecord",
    "can_view_closed_sessions",
    "normalize_visibility",
]
```

  Note: SQLite's `DateTime(timezone=True)` returns naive datetimes; `submitted_at.isoformat()` round-trips the original offset only on Postgres. The test above uses `datetime.now(UTC).isoformat()` and asserts equality — on SQLite, SQLAlchemy stores and returns the value with its `+00:00` offset preserved in the ISO string column representation. If the round-trip assertion fails on naive-datetime grounds during implementation, normalize on write with `datetime.fromisoformat(submitted_at).astimezone(UTC)` and assert `listed[0].submitted_at.startswith(submitted_at[:19])` instead — keep timezone-aware datetimes throughout (landmine list, Scope Notes).

- [ ] **Run the tests and confirm they pass.** Run: `python -m pytest tests/test_production_depth_public_archive_persistence.py -x -q` — expect `4 passed`.

- [ ] **Run the milestone 8 suite to prove no regression.** Run: `python -m pytest tests/test_milestone_8_public_archive.py tests/test_milestone_2_schema_and_migrations.py -q` — expect all passed.

- [ ] **Commit.** Run: `git add civicclerk/public_archive.py civicclerk/migrations/versions/civicclerk_0014_public_meeting_records.py tests/test_production_depth_public_archive_persistence.py && git commit -s -m "feat(persistence): add public archive and comment repositories"`

---

## Task 4: main.py env-gated wiring + idempotent demo seed

**Files:**
- Modify: `civicclerk/main.py` (imports L54-55/L73, module globals after L167, seed wiring L177-187, staff dashboard L578-579, every `motion_votes.` / `minutes_drafts.` / `public_archive.` / `public_comments.` call site listed below, lazy getters after `_get_vendor_sync_repository` ~L3399-3405)
- Modify: `civicclerk/demo_seed.py` (docstring L51-57, type hints, helper renames L300-368)
- Test: `tests/test_production_depth_workflow_wiring.py` (new)

### Steps

- [ ] **Write the failing tests.** Create `tests/test_production_depth_workflow_wiring.py`:

```python
from __future__ import annotations

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


def test_getters_select_repositories_when_env_set(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_MOTION_VOTE_DB_URL", f"sqlite:///{tmp_path / 'mv.db'}")
    monkeypatch.setenv("CIVICCLERK_MINUTES_DB_URL", f"sqlite:///{tmp_path / 'mn.db'}")
    monkeypatch.setenv("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL", f"sqlite:///{tmp_path / 'pa.db'}")

    assert isinstance(main_module._get_motion_votes(), MotionVoteRepository)
    assert isinstance(main_module._get_minutes_drafts(), MinutesDraftRepository)
    assert isinstance(main_module._get_public_archive(), PublicArchiveRepository)
    assert isinstance(main_module._get_public_comments(), PublicCommentRepository)


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


def test_demo_seed_docstring_no_longer_claims_in_memory_only() -> None:
    from civicclerk.demo_seed import seed_demo_data

    doc = (seed_demo_data.__doc__ or "").lower()
    assert "in-memory, so they are seeded" not in doc
    assert "database-backed" in doc
```

- [ ] **Run the tests and confirm they fail for the right reason.** Run: `python -m pytest tests/test_production_depth_workflow_wiring.py -x -q` — expect `AttributeError: module 'civicclerk.main' has no attribute '_get_motion_votes'`.

- [ ] **Wire `civicclerk/main.py`.** Change imports (L54-55, L73):

```python
from civicclerk.minutes import MinutesDraftRepository, MinutesDraftStore, MinutesSentence, SourceMaterial
from civicclerk.motion_vote import MotionVoteRepository, MotionVoteStore
from civicclerk.public_archive import (
    PublicArchiveRepository,
    PublicArchiveStore,
    PublicCommentRepository,
    PublicCommentStore,
    can_view_closed_sessions,
)
```

  Add module globals after `_vendor_sync_db_url` (L167):

```python
_motion_vote_repository: MotionVoteRepository | None = None
_motion_vote_db_url: str | None = None
_minutes_draft_repository: MinutesDraftRepository | None = None
_minutes_draft_db_url: str | None = None
_public_archive_repository: PublicArchiveRepository | None = None
_public_archive_db_url: str | None = None
_public_comment_repository: PublicCommentRepository | None = None
_public_comment_db_url: str | None = None
```

  Add lazy getters after `_get_vendor_sync_repository` (~L3405), following `_get_meeting_store` (env unset → in-memory store):

```python
def _get_motion_votes() -> MotionVoteRepository | MotionVoteStore:
    global _motion_vote_db_url, _motion_vote_repository
    db_url = os.environ.get("CIVICCLERK_MOTION_VOTE_DB_URL")
    if db_url is None:
        return motion_votes
    if _motion_vote_repository is None or db_url != _motion_vote_db_url:
        _motion_vote_db_url = db_url
        _motion_vote_repository = MotionVoteRepository(db_url=db_url)
    return _motion_vote_repository


def _get_minutes_drafts() -> MinutesDraftRepository | MinutesDraftStore:
    global _minutes_draft_db_url, _minutes_draft_repository
    db_url = os.environ.get("CIVICCLERK_MINUTES_DB_URL")
    if db_url is None:
        return minutes_drafts
    if _minutes_draft_repository is None or db_url != _minutes_draft_db_url:
        _minutes_draft_db_url = db_url
        _minutes_draft_repository = MinutesDraftRepository(db_url=db_url)
    return _minutes_draft_repository


def _get_public_archive() -> PublicArchiveRepository | PublicArchiveStore:
    global _public_archive_db_url, _public_archive_repository
    db_url = os.environ.get("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL")
    if db_url is None:
        return public_archive
    if _public_archive_repository is None or db_url != _public_archive_db_url:
        _public_archive_db_url = db_url
        _public_archive_repository = PublicArchiveRepository(db_url=db_url)
    return _public_archive_repository


def _get_public_comments() -> PublicCommentRepository | PublicCommentStore:
    global _public_comment_db_url, _public_comment_repository
    db_url = os.environ.get("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL")
    if db_url is None:
        return public_comments
    if _public_comment_repository is None or db_url != _public_comment_db_url:
        _public_comment_db_url = db_url
        _public_comment_repository = PublicCommentRepository(db_url=db_url)
    return _public_comment_repository
```

  Replace every direct store reference with the getter — exact call sites (line numbers pre-edit):
  - `motion_votes.` → `_get_motion_votes().` at L578 (staff dashboard `list_recent_outcomes`), L1625 (capture_motion), L1643 (list_motions), L1652 (reject_motion_mutation get), L1666 (correct_motion), L1680/L1682 (capture_vote guard + call), L1693/L1698 (list_votes), L1707 (reject_vote_mutation get), L1721 (correct_vote), L1746/L1757 (action item source guard + create), L1775 (list_action_items), L1964 (ordinance handoff motion guard). In multi-call handlers bind once: `store = _get_motion_votes()` then use `store.` for each call so the 409/404 guard and the write hit the same backend.
  - `minutes_drafts.` → `_get_minutes_drafts().` at L579 (dashboard `list_recent`), L2057 (create_draft), L2104 (ai-assist create_draft), L2144 (list_drafts), L2152 (reject post get_draft).
  - `public_archive.` → `_get_public_archive().` at L2210 (publish), L2366 (public_calendar), L2376/L2385/L2412/L2439 (public_detail), L2469 (search).
  - `public_comments.` → `_get_public_comments().` at L2415 (submit), L2442 (list_for_record), L2450 (list_all).

  Update the seed wiring inside `seed_demo_data_when_requested` (L177-187):

```python
    seed_demo_data(
        meeting_bodies=_get_meeting_body_repository(),
        meetings=_get_meeting_store(),
        agenda_intake=_get_agenda_intake_repository(),
        agenda_items=_get_agenda_items(),
        packet_assemblies=_get_packet_assembly_repository(),
        notice_checklists=_get_notice_checklist_repository(),
        motion_votes=_get_motion_votes(),
        minutes_drafts=_get_minutes_drafts(),
        public_archive=_get_public_archive(),
    )
```

- [ ] **Update `civicclerk/demo_seed.py`.** Imports become:

```python
from civicclerk.minutes import MinutesDraftRepository, MinutesDraftStore, MinutesSentence, SourceMaterial
from civicclerk.motion_vote import MotionVoteRepository, MotionVoteStore
from civicclerk.public_archive import PublicArchiveRepository, PublicArchiveStore
```

  Signature type hints become `motion_votes: MotionVoteRepository | MotionVoteStore`, `minutes_drafts: MinutesDraftRepository | MinutesDraftStore`, `public_archive: PublicArchiveRepository | PublicArchiveStore`. The existing dedupe guards (`if store.list_motions(meeting_id): return` at L306, `if store.list_drafts(meeting_id): return` at L336, `if store.public_calendar(): return` at L359) already match how DB-backed seeds dedupe today (lookup-before-create, like `_ensure_meeting_body` L150-153) and work unchanged against the repositories — keep them, rename the helpers `_seed_in_memory_outcomes` → `_ensure_meeting_outcomes`, `_seed_in_memory_minutes` → `_ensure_minutes_draft`, `_seed_in_memory_public_archive` → `_ensure_public_archive_record` (update the three call sites at L122-128), and update their parameter type hints to the unions. Replace the `seed_demo_data` docstring body (L51-57) with:

```python
    """Populate the current runtime with deterministic Brookfield demo work.

    The seed is idempotent for every store it touches: each helper looks up
    existing records before creating new ones, so a restarted Compose stack
    does not duplicate staff work. Motion, minutes, and public archive data
    seed through the same lookup-before-create pattern whether the runtime
    wires the in-memory stores or the database-backed repositories
    (CIVICCLERK_MOTION_VOTE_DB_URL, CIVICCLERK_MINUTES_DB_URL,
    CIVICCLERK_PUBLIC_ARCHIVE_DB_URL).
    """
```

- [ ] **Run the tests and confirm they pass.** Run: `python -m pytest tests/test_production_depth_workflow_wiring.py -x -q` — expect `5 passed`.

- [ ] **Run the full affected regression set.** Run: `python -m pytest tests/test_milestone_6_motion_vote_action_capture.py tests/test_milestone_7_minutes_citations.py tests/test_milestone_8_public_archive.py tests/test_demo_seed.py tests/test_milestone_13_staff_workflow_ui.py -q` — expect all passed (env vars unset → in-memory fallback, behavior identical).

- [ ] **Commit.** Run: `git add civicclerk/main.py civicclerk/demo_seed.py tests/test_production_depth_workflow_wiring.py && git commit -s -m "feat(persistence): env-gate workflow repositories and make demo seed idempotent"`

---

## Task 5: HTTP-level restart-survival proof + README Release Recovery Notice

**Files:**
- Modify: `README.md` (Release Recovery Notice section, after the existing paragraph ~L10-22)
- Test: `tests/test_production_depth_legal_record_persistence.py` (new)

### Steps

- [ ] **Write the failing integration test.** Create `tests/test_production_depth_legal_record_persistence.py`:

```python
from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient

import civicclerk.main as main_module

ROOT = Path(__file__).resolve().parents[1]


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


async def test_legal_record_survives_api_restart_when_db_env_vars_set(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("CIVICCLERK_MEETING_DB_URL", f"sqlite:///{tmp_path / 'meetings.db'}")
    monkeypatch.setenv("CIVICCLERK_MOTION_VOTE_DB_URL", f"sqlite:///{tmp_path / 'motions.db'}")
    monkeypatch.setenv("CIVICCLERK_MINUTES_DB_URL", f"sqlite:///{tmp_path / 'minutes.db'}")
    monkeypatch.setenv("CIVICCLERK_PUBLIC_ARCHIVE_DB_URL", f"sqlite:///{tmp_path / 'archive.db'}")
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
    assert draft.status_code == 201, draft.json()
    assert record.status_code == 201
    assert comment.status_code == 201

    _simulate_process_restart()

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        motions_after = await client.get(f"/meetings/{meeting_id}/motions")
        votes_after = await client.get(f"/motions/{motion_id}/votes")
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
```

  Note: `comments_after` reads from the endpoint at `civicclerk/main.py:2436-2442` whose response wraps comments — if the key is not `"comments"`, match the actual key from that handler when writing the test (inspect L2442-2447 before finalizing; do not change the response shape).

- [ ] **Run the tests and confirm they fail for the right reason.** Run: `python -m pytest tests/test_production_depth_legal_record_persistence.py -x -q` — expect the README test to fail with `AssertionError` on `CIVICCLERK_MOTION_VOTE_DB_URL` (and the integration test to fail only if Tasks 1-4 are incomplete; with Tasks 1-4 done it should already pass, proving the wiring).

- [ ] **Update `README.md`.** Append this exact paragraph to the end of the `## Release Recovery Notice` section (after the existing paragraph ending "...claiming a live production deployment."):

```markdown
Persistence Phase 1 update: motions, votes, action items, minutes drafts,
public archive records, and resident comments now persist to the configured
database when `CIVICCLERK_MOTION_VOTE_DB_URL`, `CIVICCLERK_MINUTES_DB_URL`,
and `CIVICCLERK_PUBLIC_ARCHIVE_DB_URL` are set, so the legal record of a
meeting survives an API restart. Without those variables CivicMeetings falls
back to in-memory stores and the legal record does not survive a restart —
do not run a real public meeting without database-backed persistence
enabled. Transcript records, ordinance/resolution handoffs, notice records,
and packet snapshots remain in-memory pending Persistence Phase 1b.
```

- [ ] **Run the tests and confirm they pass.** Run: `python -m pytest tests/test_production_depth_legal_record_persistence.py -x -q` — expect `2 passed`.

- [ ] **Run the full suite.** Run: `python -m pytest -q` — expect zero failures (the milestone-6 doc test forbids "minutes drafting shipped" / "archive workflow shipped" phrasing; the wording above avoids both).

- [ ] **Commit.** Run: `git add README.md tests/test_production_depth_legal_record_persistence.py && git commit -s -m "test(persistence): prove legal record survives restart at HTTP level"`

---

## Scope Notes

**Explicitly OUT of Phase 1 (each needs schema design first; they are Phase 1b with their own plan):**
- **Transcripts table redesign** — the in-memory transcript dicts (`civicclerk/main.py:2163-2198`: `actor`, `source_label`, `transcript_text`, `public_release_requested`, `closed_session`, embedded `message`/`fix`) do not map onto the canonical `transcripts` table (`source_uri`, `document_ref`, `sensitivity_label`, `staff_acl_roles` — models.py L180-193). Persisting them requires deciding where transcript text lives (column vs document store) and how closed-session ACLs apply.
- **`ordinance_resolution_handoffs` table** — the handoff dicts (`civicclerk/main.py:1975-2001`) carry CivicCode emit state machines (`civiccode_handoff_status`, retry bookkeeping, event ids) with no canonical table at all; needs a designed table plus a decision on retry-state ownership.
- **NoticeStore persistence** (`civicclerk/packet_notice.py`) — the canonical `notices` table exists but the store's compliance-result shape needs mapping work against `NoticeChecklistRepository`, which already persists overlapping data; persisting both without a reconciliation design would fork the record.
- **PacketStore snapshots** (`civicclerk/packet_notice.py`) — snapshot content vs the canonical `packet_versions.snapshot_uri` (URI, not blob) needs a storage design decision.

**Landmines inventoried — every task must respect these:**
- **Response-shape contracts:** the frontend types pin motion `{id, meeting_id, agenda_item_id, text, actor, seconded_by, correction_of_id, correction_reason, captured}`, vote, action-item, minutes-draft, and public-record payloads exactly. The repositories return the SAME dataclasses (`MotionRecord`, `VoteRecord`, `ActionItemRecord`, `MinutesDraft`, `PublicMeetingRecord`, `PublicCommentRecord`), so `public_dict()` is the single serialization path. `actor` maps to the `captured_by` column for motions; `captured` is derived (always `True`) and never stored.
- **Immutability 409s:** PUT/PATCH on `/motions/{id}` and `/votes/{id}` still return 409 with the exact `message`/`fix` strings (handlers at `civicclerk/main.py:1648-1660`, L1703-1715 are untouched — only the lookup behind them swaps). `POST /minutes/{id}/post` keeps its 409. Corrections remain append-only inserts; repositories expose no update/delete.
- **`_normalize_optional_text` replication:** `motion_vote.py` and `public_archive.py` each already define it (L260-264 and L194-198 respectively); the repositories reuse the module-local copies — do not import across modules and do not skip the strip-to-None semantics (`seconded_by`, `plain_language_summary`, `minutes_adopted_at`, `minutes_signed_by`).
- **Self-referential correction FKs:** `motions.correction_of_id → motions.id` and `votes.correction_of_id → votes.id` exist on Postgres (models.py L105, L122). Corrections insert AFTER reading the original in the same repository, so FK order is satisfied; mirror tables on SQLite declare no FKs (matching `meeting_body.py` precedent), so SQLite demos can't violate them either.
- **Timezone-aware datetimes:** all writes use `datetime.now(UTC)`; columns are `DateTime(timezone=True)`. SQLite returns naive datetimes — the repositories never compare datetimes across rows except via `ORDER BY`, and the only datetime that round-trips into a response (`public_comments.submitted_at`) is re-serialized with `.isoformat()`. Task 3 documents the fallback assertion if SQLite drops the offset.
- **Non-UUID passthrough ids:** `agenda_item_id` on motion capture is an unvalidated optional string in the API. The canonical column is `uuid`. The repository stores `NULL` for non-UUID values (`_uuid_text_or_none`) instead of crashing; real flows always pass UUIDs (AgendaItemRepository/Store generate them). This is a deliberate, documented narrowing in DB mode.
- **Ordering:** in-memory stores preserve insertion order via dicts/lists; repositories use `ORDER BY created_at ASC, id ASC` everywhere a list is returned (spec requirement). The `id ASC` tiebreaker makes same-microsecond inserts deterministic, though not strictly insertion-ordered — acceptable because correction flows always read the original first, guaranteeing a later `created_at`.
- **Audit-chain integration (decision taken):** the new repositories record `AuditHashChain` events for every write, matching `AgendaIntakeRepository` (`agenda_intake.py:109,140-150`). Motion/vote event hashes persist into the existing `immutable_hash` columns; `action_items`, `minutes`, and the archive tables have no hash column, so their chains are in-process attestations only (same lifecycle as AgendaIntakeRepository's chain, which also restarts empty). Hashes are NOT added to any response payload — contracts unchanged. A durable cross-restart audit ledger is a Phase 1b candidate.
- **Demo seed dedupe:** the lookup-before-create guards in `demo_seed.py` are the dedupe mechanism for DB-backed stores (same as `_ensure_meeting_body`); Task 4 keeps them and proves idempotence across fresh repository instances.

---

## Self-Review

- **Spec coverage:** Task 1 delivers MotionVoteRepository on the existing `motions`/`votes`/`action_items` tables with `CIVICCLERK_MOTION_VOTE_DB_URL`, actor→captured_by mapping, derived `captured`, the `action_items.actor` migration (0012), `ORDER BY created_at ASC, id ASC`, append-only corrections with 409s preserved, and the instance-A/instance-B restart-survival test with no in-memory fallback. Task 2 delivers MinutesDraftRepository (`CIVICCLERK_MINUTES_DB_URL`) with sentences→`sentence_citations` JSON, source_materials→JSON, provenance decomposed (model column added by migration 0013 — choice documented), adopted derived from `adopted_at`, posted from the new `posted_at` column. Task 3 delivers the new `public_meeting_records` table (migration 0014, columns matching the dataclass) plus PublicCommentRepository on the existing `public_comments` table with comment→body and visibility defaulting to public. Task 4 wires env-gated lazy getters with in-memory fallback and makes the demo seed idempotent with an honest docstring. Task 5 proves restart survival at the HTTP level across all four stores and updates the README Release Recovery Notice with exact wording. Scope Notes list all four Phase 1b exclusions and all inventoried landmines including the audit-chain decision.
- **No placeholders:** every test block and implementation block above is complete, runnable code; no "TBD", no "similar to task N" references — repeated patterns (engine setup, UUID helpers) are written out in full in each module they belong to.
- **Type consistency:** repositories return the exact dataclasses the in-memory stores return, so every endpoint's `public_dict()` output is bit-identical between modes; getter return types are `Repository | Store` unions matching the `_get_agenda_items`/`_get_meeting_store` precedent; `sa.Uuid(as_uuid=False)` keeps ids as `str` end-to-end against both SQLite and the Postgres `uuid` canonical columns; all timestamps are timezone-aware UTC.
- **Regression safety:** each task runs its milestone suite (6/7/8), milestone 2 (schema/migrations), demo seed, and staff UI tests before committing; Task 5 ends with the full `python -m pytest -q`. The in-memory stores are never modified, so the no-env-var path is provably unchanged.
- **Hard Rule 11:** this plan file satisfies the Superpowers Plan Gate for every commit listed above.
