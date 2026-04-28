"""Create notice checklist records table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civicclerk.migrations.guards import idempotent_create_table


revision = "civicclerk_0004_notice_ck"
down_revision = "civicclerk_0003_packet_asm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "notice_checklist_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("meeting_id", sa.String(64), nullable=False),
        sa.Column("notice_type", sa.String(120), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("compliant", sa.Boolean(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("minimum_notice_hours", sa.Integer(), nullable=False),
        sa.Column("statutory_basis", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("posting_proof", postgresql.JSONB(), nullable=True),
        sa.Column("last_audit_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civicclerk",
    )


def downgrade() -> None:
    op.drop_table("notice_checklist_records", schema="civicclerk")
