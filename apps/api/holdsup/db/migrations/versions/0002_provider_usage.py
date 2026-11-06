"""Add provider_usage for the model router's daily budgets.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_usage",
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("provider", "day", name=op.f("pk_provider_usage")),
    )


def downgrade() -> None:
    op.drop_table("provider_usage")
