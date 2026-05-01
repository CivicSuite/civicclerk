"""Add editable meeting scheduling fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "civicclerk_0007_meeting_schedule"
down_revision = "civicclerk_0006_agenda_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _add_column_if_missing(
        "meeting_records",
        sa.Column("meeting_body_id", sa.String(64), nullable=True),
        schema="civicclerk",
    )
    _add_column_if_missing(
        "meeting_records",
        sa.Column("location", sa.String(255), nullable=True),
        schema="civicclerk",
    )


def downgrade() -> None:
    _drop_column_if_present("meeting_records", "location", schema="civicclerk")
    _drop_column_if_present("meeting_records", "meeting_body_id", schema="civicclerk")


def _add_column_if_missing(table_name: str, column: sa.Column, *, schema: str) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {item["name"] for item in inspector.get_columns(table_name, schema=schema)}
    if column.name not in existing:
        op.add_column(table_name, column, schema=schema)


def _drop_column_if_present(table_name: str, column_name: str, *, schema: str) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {item["name"] for item in inspector.get_columns(table_name, schema=schema)}
    if column_name in existing:
        op.drop_column(table_name, column_name, schema=schema)
