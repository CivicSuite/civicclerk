"""Create persisted meeting records table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civicclerk.migrations.guards import idempotent_create_table


revision = "civicclerk_0005_meetings"
down_revision = "civicclerk_0004_notice_ck"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "meeting_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("meeting_type", sa.String(80), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("audit_entries", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civicclerk",
    )


def downgrade() -> None:
    op.drop_table("meeting_records", schema="civicclerk")
