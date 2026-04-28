"""Create agenda intake queue table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civicclerk.migrations.guards import idempotent_create_table


revision = "civicclerk_0002_intake_queue"
down_revision = "civicclerk_0001_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "agenda_intake_queue",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("department_name", sa.String(255), nullable=False),
        sa.Column("submitted_by", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("readiness_status", sa.String(80), nullable=False),
        sa.Column("reviewer", sa.String(255), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("source_references", postgresql.JSONB(), nullable=False),
        sa.Column("last_audit_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civicclerk",
    )


def downgrade() -> None:
    op.drop_table("agenda_intake_queue", schema="civicclerk")
