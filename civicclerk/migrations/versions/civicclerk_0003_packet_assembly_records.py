"""Create packet assembly records table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civicclerk.migrations.guards import idempotent_create_table


revision = "civicclerk_0003_packet_asm"
down_revision = "civicclerk_0002_intake_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "packet_assembly_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("meeting_id", sa.String(64), nullable=False),
        sa.Column("packet_snapshot_id", sa.String(64), nullable=False),
        sa.Column("packet_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("agenda_item_ids", postgresql.JSONB(), nullable=False),
        sa.Column("source_references", postgresql.JSONB(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False),
        sa.Column("finalized_by", sa.String(255), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_audit_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civicclerk",
    )


def downgrade() -> None:
    op.drop_table("packet_assembly_records", schema="civicclerk")
