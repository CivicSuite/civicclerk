"""Add vendor live-sync success cursor."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "civicclerk_0010_vendor_cursor"
down_revision = "civicclerk_0009_vendor_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("vendor_sync_sources", schema="civicclerk")
    }
    if "last_success_cursor_at" not in columns:
        op.add_column(
            "vendor_sync_sources",
            sa.Column("last_success_cursor_at", sa.DateTime(timezone=True), nullable=True),
            schema="civicclerk",
        )


def downgrade() -> None:
    op.drop_column("vendor_sync_sources", "last_success_cursor_at", schema="civicclerk")
