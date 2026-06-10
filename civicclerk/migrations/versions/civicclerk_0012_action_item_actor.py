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
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("action_items", schema=SCHEMA)
    }
    if "actor" in columns:
        op.drop_column("action_items", "actor", schema=SCHEMA)
