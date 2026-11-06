"""Add series_cache for 24-hour reuse of fetched series.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "series_cache",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=200), nullable=False),
        sa.Column("query_key", sa.String(length=64), nullable=False),
        sa.Column("geo", sa.Text(), nullable=False, server_default=""),
        sa.Column("filters", postgresql.JSONB(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_sha256", sa.String(length=64), nullable=False),
        sa.Column("rows", postgresql.JSONB(), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_series_cache")),
        sa.UniqueConstraint("source", "code", "query_key", name=op.f("uq_series_cache_source")),
    )


def downgrade() -> None:
    op.drop_table("series_cache")
