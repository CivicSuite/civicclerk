"""CivicClerk-specific Alembic guards."""

from __future__ import annotations

from typing import Any

import alembic.op as op
import sqlalchemy as sa


def idempotent_create_table(name: str, *columns: Any, **kwargs: Any) -> None:
    """Create a table unless it already exists in the target schema."""
    schema = kwargs.get("schema")
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(name, schema=schema):
        return
    op.create_table(name, *columns, **kwargs)
