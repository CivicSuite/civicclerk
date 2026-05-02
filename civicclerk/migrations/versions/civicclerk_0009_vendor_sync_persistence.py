"""Create vendor live-sync persistence tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from civicclerk.migrations.guards import idempotent_create_table


revision = "civicclerk_0009_vendor_sync"
down_revision = "civicclerk_0008_intake_promotion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "vendor_sync_sources",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("connector", sa.String(80), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("auth_method", sa.String(80), nullable=False),
        sa.Column("consecutive_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sync_paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sync_paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_paused_reason", sa.String(255), nullable=True),
        sa.Column("last_sync_status", sa.String(80), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civicclerk",
    )
    idempotent_create_table(
        "vendor_sync_run_log",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("records_discovered", sa.Integer(), nullable=False),
        sa.Column("records_succeeded", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        sa.Column("retries_attempted", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["civicclerk.vendor_sync_sources.id"],
            ondelete="CASCADE",
        ),
        schema="civicclerk",
    )
    idempotent_create_table(
        "vendor_sync_failures",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_id", sa.String(64), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("error_class", sa.String(200), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("first_failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["civicclerk.vendor_sync_sources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["civicclerk.vendor_sync_run_log.id"],
            ondelete="CASCADE",
        ),
        schema="civicclerk",
    )


def downgrade() -> None:
    op.drop_table("vendor_sync_failures", schema="civicclerk")
    op.drop_table("vendor_sync_run_log", schema="civicclerk")
    op.drop_table("vendor_sync_sources", schema="civicclerk")
