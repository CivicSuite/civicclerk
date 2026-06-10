"""Add archive read-path indexes.

public_comments.public_record_id backs the resident comment listing on each
public meeting record, and every capture_seq column added in 0015 backs the
deterministic ORDER BY on repository list reads. Both were sequential scans.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "civicclerk_0016_archive_indexes"
down_revision = "civicclerk_0015_capture_seq"
branch_labels = None
depends_on = None

SCHEMA = "civicclerk"

CAPTURE_SEQ_TABLES = (
    "motions",
    "votes",
    "action_items",
    "minutes",
    "public_meeting_records",
    "public_comments",
)


def _index_targets() -> list[tuple[str, str, str]]:
    targets = [
        (
            "ix_civicclerk_public_comments_public_record_id",
            "public_comments",
            "public_record_id",
        )
    ]
    targets.extend(
        (f"ix_civicclerk_{table_name}_capture_seq", table_name, "capture_seq")
        for table_name in CAPTURE_SEQ_TABLES
    )
    return targets


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for index_name, table_name, column_name in _index_targets():
        existing = {
            index["name"]
            for index in inspector.get_indexes(table_name, schema=SCHEMA)
        }
        if index_name in existing:
            continue
        op.create_index(index_name, table_name, [column_name], schema=SCHEMA)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for index_name, table_name, _column_name in _index_targets():
        existing = {
            index["name"]
            for index in inspector.get_indexes(table_name, schema=SCHEMA)
        }
        if index_name in existing:
            op.drop_index(index_name, table_name=table_name, schema=SCHEMA)
