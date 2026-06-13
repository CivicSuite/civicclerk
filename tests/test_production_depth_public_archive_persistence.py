from __future__ import annotations

import importlib.util
import inspect
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient

from civicclerk import public_archive as public_archive_module
from civicclerk.main import app
from civicclerk.public_archive import (
    PublicArchiveRepository,
    PublicCommentRepository,
)

ROOT = Path(__file__).resolve().parents[1]


def seed_meeting(db_url: str) -> str:
    """Insert a minimal civicclerk.meetings parent row so publishes pass the FK pre-check."""

    meeting_id = str(uuid4())
    engine = sa.create_engine(db_url, future=True)
    if engine.dialect.name == "sqlite":
        engine = engine.execution_options(schema_translate_map={"civicclerk": None})
    public_archive_module.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            public_archive_module.meetings_table.insert().values(id=meeting_id)
        )
    engine.dispose()
    return meeting_id


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

        @classmethod
        def fromisoformat(cls, value):  # noqa: ANN001 - mirrors datetime API
            return datetime.fromisoformat(value)

    monkeypatch.setattr(module, "datetime", FrozenDatetime)
    return frozen


def test_public_records_persist_across_repository_instances(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'archive.db'}"
    meeting_id = seed_meeting(db_url)

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
    assert second.public_detail("not-a-uuid") is None
    assert [r.id for r in second.search(query="sidewalk")] == [record.id]
    assert second.search(query="zzz-no-match") == []


def test_closed_session_records_hidden_from_public_surfaces(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'closed.db'}"
    repo = PublicArchiveRepository(db_url=db_url)
    closed = repo.publish(
        meeting_id=seed_meeting(db_url),
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
        meeting_id=seed_meeting(db_url),
        title="Open Comment Meeting",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
        public_comment_enabled=True,
    )
    closed_record = archive.publish(
        meeting_id=seed_meeting(db_url),
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
    assert second.list_for_record("not-a-uuid") == []


def test_comments_against_unpersisted_records_are_rejected(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'orphan.db'}"
    elsewhere_url = f"sqlite:///{tmp_path / 'elsewhere.db'}"
    other_db = PublicArchiveRepository(db_url=elsewhere_url)
    phantom = other_db.publish(
        meeting_id=seed_meeting(elsewhere_url),
        title="Record That Lives In Another Database",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
        public_comment_enabled=True,
    )

    comments = PublicCommentRepository(db_url=db_url)
    rejected = comments.submit(
        public_record=phantom,
        commenter_name="Resident Lee",
        comment="The parent record never landed in this database.",
        submitted_at=datetime.now(UTC).isoformat(),
    )

    assert rejected is None
    assert comments.list_all() == []
    assert comments.audit_chain.events == []


def test_concurrent_publishes_keep_audit_chain_intact(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'concurrent.db'}"
    repo = PublicArchiveRepository(db_url=db_url)
    meeting_id = seed_meeting(db_url)

    def publish_batch(worker_index: int) -> None:
        for sequence in range(25):
            record = repo.publish(
                meeting_id=meeting_id,
                title=f"Concurrent Meeting {worker_index}-{sequence}",
                visibility="public",
                posted_agenda="Agenda.",
                posted_packet="Packet.",
                approved_minutes="Minutes.",
            )
            assert record is not None and record.id

    # Force frequent thread switches so unsynchronized read-last-hash-then-append
    # interleavings surface deterministically instead of once a month in production.
    original_interval = sys.getswitchinterval()
    try:
        sys.setswitchinterval(1e-6)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(publish_batch, range(8)))
    finally:
        sys.setswitchinterval(original_interval)

    assert len(repo.public_calendar()) == 200
    assert len(repo.audit_chain.events) == 200
    assert repo.audit_chain.verify()


def test_concurrent_comment_submissions_keep_audit_chain_intact(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'concurrent_comments.db'}"
    archive = PublicArchiveRepository(db_url=db_url)
    open_record = archive.publish(
        meeting_id=seed_meeting(db_url),
        title="Open Comment Meeting",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
        public_comment_enabled=True,
    )
    repo = PublicCommentRepository(db_url=db_url)
    submitted_at = datetime.now(UTC).isoformat()

    def submit_batch(worker_index: int) -> None:
        for sequence in range(25):
            comment = repo.submit(
                public_record=open_record,
                commenter_name=f"Resident {worker_index}",
                comment=f"Concurrent comment {worker_index}-{sequence}.",
                submitted_at=submitted_at,
            )
            assert comment is not None

    # Force frequent thread switches so unsynchronized read-last-hash-then-append
    # interleavings surface deterministically instead of once a month in production.
    original_interval = sys.getswitchinterval()
    try:
        sys.setswitchinterval(1e-6)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(submit_batch, range(8)))
    finally:
        sys.setswitchinterval(original_interval)

    assert len(repo.list_for_record(open_record.id)) == 200
    assert len(repo.audit_chain.events) == 200
    assert repo.audit_chain.verify()


def test_same_timestamp_publishes_and_comments_preserve_insertion_order(
    tmp_path, monkeypatch
) -> None:
    """Records and comments inserted within one tick must list in insertion order."""

    freeze_module_clock(monkeypatch, public_archive_module)
    db_url = f"sqlite:///{tmp_path / 'same-tick.db'}"
    archive = PublicArchiveRepository(db_url=db_url)
    meeting_id = seed_meeting(db_url)

    records = [
        archive.publish(
            meeting_id=meeting_id,
            title=f"Sidewalk Hearing #{index}",
            visibility="public",
            posted_agenda=f"Agenda #{index} covering sidewalk repairs.",
            posted_packet=f"Packet #{index}.",
            approved_minutes=f"Minutes #{index}.",
            public_comment_enabled=True,
        )
        for index in range(24)
    ]
    assert [r.id for r in archive.public_calendar()] == [r.id for r in records]
    assert [r.id for r in archive.search(query="sidewalk")] == [r.id for r in records]

    comments_repo = PublicCommentRepository(db_url=db_url)
    comments = [
        comments_repo.submit(
            public_record=records[0],
            commenter_name=f"Resident {index}",
            comment=f"Comment #{index}.",
            submitted_at="2026-06-10T12:00:00+00:00",
        )
        for index in range(24)
    ]
    assert all(comment is not None for comment in comments)
    assert [c.id for c in comments_repo.list_for_record(records[0].id)] == [
        c.id for c in comments
    ]
    assert [c.id for c in comments_repo.list_all()] == [c.id for c in comments]


def test_publish_rejects_unknown_meeting_referent(tmp_path) -> None:
    """publish() must pre-check the meetings FK referent like other repositories."""

    db_url = f"sqlite:///{tmp_path / 'unknown-meeting.db'}"
    repo = PublicArchiveRepository(db_url=db_url)

    rejected = repo.publish(
        meeting_id=str(uuid4()),
        title="Record For A Meeting That Does Not Exist",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
    )

    assert rejected is None
    assert repo.public_calendar() == []
    assert repo.audit_chain.events == []


def test_comment_gate_trusts_database_row_not_caller_snapshot(tmp_path) -> None:
    """submit() must gate on the persisted row, not the caller-supplied snapshot."""

    db_url = f"sqlite:///{tmp_path / 'snapshot-lies.db'}"
    archive = PublicArchiveRepository(db_url=db_url)
    closed_record = archive.publish(
        meeting_id=seed_meeting(db_url),
        title="Closed Session - Litigation",
        visibility="closed_session",
        posted_agenda="Closed agenda.",
        posted_packet="Closed packet.",
        approved_minutes="Closed minutes.",
    )
    disabled_record = archive.publish(
        meeting_id=seed_meeting(db_url),
        title="Comment Intake Disabled Meeting",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
        public_comment_enabled=False,
    )
    assert closed_record is not None and disabled_record is not None

    comments = PublicCommentRepository(db_url=db_url)
    submitted_at = datetime.now(UTC).isoformat()

    lying_closed_snapshot = replace(
        closed_record, visibility="public", public_comment_enabled=True
    )
    rejected_closed = comments.submit(
        public_record=lying_closed_snapshot,
        commenter_name="Resident Lee",
        comment="The database row says closed_session.",
        submitted_at=submitted_at,
    )

    lying_disabled_snapshot = replace(disabled_record, public_comment_enabled=True)
    rejected_disabled = comments.submit(
        public_record=lying_disabled_snapshot,
        commenter_name="Resident Lee",
        comment="The database row says comment intake is disabled.",
        submitted_at=submitted_at,
    )

    assert rejected_closed is None
    assert rejected_disabled is None
    assert comments.list_all() == []
    assert comments.audit_chain.events == []


def test_comment_meeting_id_written_from_database_row(tmp_path) -> None:
    """submit() must persist the parent row's meeting_id even when the snapshot lies."""

    db_url = f"sqlite:///{tmp_path / 'meeting-id-truth.db'}"
    archive = PublicArchiveRepository(db_url=db_url)
    true_meeting_id = seed_meeting(db_url)
    open_record = archive.publish(
        meeting_id=true_meeting_id,
        title="Open Comment Meeting",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
        public_comment_enabled=True,
    )
    assert open_record is not None

    comments = PublicCommentRepository(db_url=db_url)
    lying_snapshot = replace(open_record, meeting_id=str(uuid4()))
    comment = comments.submit(
        public_record=lying_snapshot,
        commenter_name="Resident Lee",
        comment="The meeting id must come from the database row.",
        submitted_at=datetime.now(UTC).isoformat(),
    )
    assert comment is not None

    engine = sa.create_engine(db_url, future=True).execution_options(
        schema_translate_map={"civicclerk": None}
    )
    with engine.begin() as connection:
        stored_meeting_id = connection.execute(
            sa.select(public_archive_module.public_comments_table.c.meeting_id).where(
                public_archive_module.public_comments_table.c.id == comment.id
            )
        ).scalar_one()
    engine.dispose()

    assert str(stored_meeting_id) == true_meeting_id


def test_blank_or_oversized_comment_inputs_rejected_before_write(tmp_path) -> None:
    """submit() must reject blank/oversized resident input before touching the chain."""

    db_url = f"sqlite:///{tmp_path / 'input-guard.db'}"
    archive = PublicArchiveRepository(db_url=db_url)
    open_record = archive.publish(
        meeting_id=seed_meeting(db_url),
        title="Open Comment Meeting",
        visibility="public",
        posted_agenda="Agenda.",
        posted_packet="Packet.",
        approved_minutes="Minutes.",
        public_comment_enabled=True,
    )
    assert open_record is not None

    comments = PublicCommentRepository(db_url=db_url)
    submitted_at = datetime.now(UTC).isoformat()

    blank_name = comments.submit(
        public_record=open_record,
        commenter_name="   ",
        comment="A real comment.",
        submitted_at=submitted_at,
    )
    blank_comment = comments.submit(
        public_record=open_record,
        commenter_name="Resident Lee",
        comment="   ",
        submitted_at=submitted_at,
    )
    oversized_name = comments.submit(
        public_record=open_record,
        commenter_name="x" * 256,
        comment="A real comment.",
        submitted_at=submitted_at,
    )

    assert blank_name is None
    assert blank_comment is None
    assert oversized_name is None
    assert comments.list_all() == []
    assert comments.audit_chain.events == []


async def test_api_comment_model_enforces_name_bounds(monkeypatch) -> None:
    """The HTTP model must 422 oversized names; whitespace-only names never persist."""

    from civicclerk import main as main_module
    from civicclerk.public_archive import PublicArchiveStore, PublicCommentStore

    # Fresh in-memory stores so this test never leaks records into the
    # module-level state shared with the milestone-8 HTTP tests.
    monkeypatch.setattr(main_module, "public_archive", PublicArchiveStore())
    monkeypatch.setattr(main_module, "public_comments", PublicCommentStore())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Comment Bounds Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-06-10T19:00:00Z",
            },
        )
        assert meeting.status_code == 201
        record = await client.post(
            f"/meetings/{meeting.json()['id']}/public-record",
            json={
                "title": "Comment Bounds Meeting",
                "visibility": "public",
                "posted_agenda": "Agenda.",
                "posted_packet": "Packet.",
                "approved_minutes": "Minutes.",
                "public_comment_enabled": True,
            },
        )
        assert record.status_code == 201
        record_id = record.json()["id"]

        oversized = await client.post(
            f"/public/meetings/{record_id}/comments",
            json={"commenter_name": "x" * 256, "comment": "A real comment."},
        )
        assert oversized.status_code == 422

        whitespace_only = await client.post(
            f"/public/meetings/{record_id}/comments",
            json={"commenter_name": "   ", "comment": "A real comment."},
        )
        assert whitespace_only.status_code == 409

        listed = await client.get(f"/public/meetings/{record_id}/comments")
        assert listed.status_code == 200
        assert listed.json()["total_count"] == 0


def test_migration_0016_creates_archive_indexes() -> None:
    path = (
        ROOT
        / "civicclerk"
        / "migrations"
        / "versions"
        / "civicclerk_0016_archive_indexes.py"
    )
    assert path.exists(), "Missing migration: civicclerk_0016_archive_indexes.py"
    spec = importlib.util.spec_from_file_location("civicclerk_0016_archive_indexes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "civicclerk_0016_archive_indexes"
    assert module.down_revision == "civicclerk_0015_capture_seq"
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    # Spec review: the migration must actually target the comment listing
    # column and every capture_seq table, not merely declare the chain.
    module_source = inspect.getsource(module)
    assert "public_record_id" in module_source
    assert "capture_seq" in module_source
    for table_name in (
        "motions",
        "votes",
        "action_items",
        "minutes",
        "public_meeting_records",
        "public_comments",
    ):
        assert table_name in inspect.getsource(module)


def test_migration_0014_creates_public_meeting_records_and_extends_chain() -> None:
    path = (
        ROOT
        / "civicclerk"
        / "migrations"
        / "versions"
        / "civicclerk_0014_public_meeting_records.py"
    )
    assert path.exists(), "Missing migration: civicclerk_0014_public_meeting_records.py"
    spec = importlib.util.spec_from_file_location("civicclerk_0014_public_meeting_records", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "civicclerk_0014_public_records"
    assert module.down_revision == "civicclerk_0013_minutes_model"
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    # Spec review: the upgrade must actually target the public_meeting_records
    # table, not merely declare the revision chain.
    assert "public_meeting_records" in inspect.getsource(module.upgrade)
