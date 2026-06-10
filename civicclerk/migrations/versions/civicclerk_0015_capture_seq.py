"""Add capture_seq insertion-order columns for deterministic list reads.

Repository list paths previously ordered by (created_at, id); same-timestamp
rows tiebroke on a random uuid4 and lost insertion order. capture_seq is an
app-allocated monotonic sequence (MAX+1 inside the insert transaction, under
each repository's _chain_lock) so the same repository code orders
deterministically on both SQLite mirrors and migrated PostgreSQL.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "civicclerk_0015_capture_seq"
down_revision = "civicclerk_0014_public_records"
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


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name in CAPTURE_SEQ_TABLES:
        columns = {
            column["name"]
            for column in inspector.get_columns(table_name, schema=SCHEMA)
        }
        if "capture_seq" in columns:
            continue
        op.add_column(
            table_name,
            sa.Column("capture_seq", sa.BigInteger(), nullable=True),
            schema=SCHEMA,
        )
        # Backfill pre-existing rows ordered by (created_at, id) so legacy
        # data keeps its best-known order before NOT NULL is enforced.
        op.execute(
            sa.text(
                f"""
                UPDATE {SCHEMA}.{table_name} AS target
                SET capture_seq = ranked.rn
                FROM (
                    SELECT id, row_number() OVER (ORDER BY created_at, id) AS rn
                    FROM {SCHEMA}.{table_name}
                ) AS ranked
                WHERE target.id = ranked.id
                """
            )
        )
        op.alter_column(table_name, "capture_seq", nullable=False, schema=SCHEMA)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name in CAPTURE_SEQ_TABLES:
        columns = {
            column["name"]
            for column in inspector.get_columns(table_name, schema=SCHEMA)
        }
        if "capture_seq" in columns:
            op.drop_column(table_name, "capture_seq", schema=SCHEMA)
