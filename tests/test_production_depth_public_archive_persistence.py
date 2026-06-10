from __future__ import annotations

import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
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
    assert second.public_detail("not-a-uuid") is None
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
    assert second.list_for_record("not-a-uuid") == []


def test_comments_against_unpersisted_records_are_rejected(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'orphan.db'}"
    other_db = PublicArchiveRepository(
        db_url=f"sqlite:///{tmp_path / 'elsewhere.db'}"
    )
    phantom = other_db.publish(
        meeting_id=str(uuid4()),
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
    repo = PublicArchiveRepository(db_url=f"sqlite:///{tmp_path / 'concurrent.db'}")

    def publish_batch(worker_index: int) -> None:
        for sequence in range(25):
            record = repo.publish(
                meeting_id=str(uuid4()),
                title=f"Concurrent Meeting {worker_index}-{sequence}",
                visibility="public",
                posted_agenda="Agenda.",
                posted_packet="Packet.",
                approved_minutes="Minutes.",
            )
            assert record.id

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
        meeting_id=str(uuid4()),
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
