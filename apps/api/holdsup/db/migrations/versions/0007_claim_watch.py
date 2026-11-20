"""Add the claim watch's columns to checks (S1): when a check's figures were last compared
with the sources, and the newest check computed again from it after they were revised.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("checks", sa.Column("watched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("checks", sa.Column("updated_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_checks_updated_by_checks"),
        "checks",
        "checks",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_checks_updated_by", "checks", ["updated_by"])


def downgrade() -> None:
    op.drop_index("ix_checks_updated_by", table_name="checks")
    op.drop_constraint(op.f("fk_checks_updated_by_checks"), "checks", type_="foreignkey")
    op.drop_column("checks", "updated_by")
    op.drop_column("checks", "watched_at")
