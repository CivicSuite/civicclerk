"""Track agenda intake promotion into agenda items."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "civicclerk_0008_intake_promotion"
down_revision = "civicclerk_0007_meeting_schedule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _add_column_if_missing(
        "agenda_intake_queue",
        sa.Column("promoted_agenda_item_id", sa.String(64), nullable=True),
        schema="civicclerk",
    )
    _add_column_if_missing(
        "agenda_intake_queue",
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        schema="civicclerk",
    )
    _add_column_if_missing(
        "agenda_intake_queue",
        sa.Column("promotion_audit_hash", sa.String(128), nullable=True),
        schema="civicclerk",
    )


def downgrade() -> None:
    _drop_column_if_present("agenda_intake_queue", "promotion_audit_hash", schema="civicclerk")
    _drop_column_if_present("agenda_intake_queue", "promoted_at", schema="civicclerk")
    _drop_column_if_present("agenda_intake_queue", "promoted_agenda_item_id", schema="civicclerk")


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
