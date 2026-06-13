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
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("minutes", schema=SCHEMA)
    }
    if "posted_at" in columns:
        op.drop_column("minutes", "posted_at", schema=SCHEMA)
    if "model" in columns:
        op.drop_column("minutes", "model", schema=SCHEMA)
