"""Add checks, claims and operations (the API's results and the claim ledger).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("input_embedding", Vector(384), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("providers", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", postgresql.JSONB(), nullable=True),
        sa.Column("cached_from", sa.Uuid(), nullable=True),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cached_from"],
            ["checks.id"],
            name=op.f("fk_checks_cached_from_checks"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_checks")),
    )
    op.create_index("ix_checks_normalized_text", "checks", ["normalized_text"])
    op.create_index("ix_checks_featured_created_at", "checks", ["featured", "created_at"])
    op.execute(
        "CREATE INDEX ix_checks_input_embedding ON checks "
        "USING hnsw (input_embedding vector_cosine_ops)"
    )
    op.create_table(
        "claims",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("check_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("spec", postgresql.JSONB(), nullable=False),
        sa.Column("indicator_id", sa.String(length=100), nullable=True),
        sa.Column("verdict", sa.String(length=40), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["check_id"], ["checks.id"], name=op.f("fk_claims_check_id_checks"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claims")),
        sa.UniqueConstraint("check_id", "position", name=op.f("uq_claims_check_id")),
    )
    op.create_table(
        "operations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("claim_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("output", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["claims.id"],
            name=op.f("fk_operations_claim_id_claims"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operations")),
        sa.UniqueConstraint("claim_id", "position", name=op.f("uq_operations_claim_id")),
    )


def downgrade() -> None:
    op.drop_table("operations")
    op.drop_table("claims")
    op.drop_index("ix_checks_input_embedding", table_name="checks")
    op.drop_index("ix_checks_featured_created_at", table_name="checks")
    op.drop_index("ix_checks_normalized_text", table_name="checks")
    op.drop_table("checks")
