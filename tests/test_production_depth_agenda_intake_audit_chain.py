"""Audit-chain integrity for AgendaIntakeRepository under concurrency and failure.

These pin the same two guarantees the Phase 1 repositories carry (established
by the Task 1 review on MotionVoteRepository): the hash chain must not fork
under concurrent writers, and a failed insert must not leave a phantom event
in the chain.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa

from civicclerk.agenda_intake import AgendaIntakeRepository


def test_concurrent_submissions_keep_audit_chain_intact(tmp_path) -> None:
    repository = AgendaIntakeRepository(db_url=f"sqlite:///{tmp_path / 'intake.db'}")

    original_interval = sys.getswitchinterval()
    try:
        sys.setswitchinterval(1e-6)

        def _submit(index: int) -> None:
            repository.submit(
                title=f"Item {index}",
                department_name="Public Works",
                submitted_by=f"staff{index}@example.gov",
                summary="Concurrency probe submission.",
                source_references=[{"label": "memo", "uri": "file://memo.pdf"}],
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(_submit, range(200)))
    finally:
        sys.setswitchinterval(original_interval)

    assert len(repository.list_queue()) == 200
    assert len(repository.audit_chain.events) == 200
    assert repository.audit_chain.verify()


def test_failed_insert_leaves_no_phantom_audit_event(tmp_path) -> None:
    repository = AgendaIntakeRepository(db_url=f"sqlite:///{tmp_path / 'intake.db'}")

    with pytest.raises(sa.exc.IntegrityError):
        repository.submit(
            title=None,  # type: ignore[arg-type]  # NOT NULL violation
            department_name="Public Works",
            submitted_by="staff@example.gov",
            summary="This insert must fail.",
            source_references=[],
        )

    assert repository.audit_chain.events == []
    assert repository.audit_chain.verify()
    assert repository.list_queue() == []
