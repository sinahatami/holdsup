"""ORM models. Import every model here so Alembic autogenerate sees it."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from holdsup.db.base import Base


class ProviderUsage(Base):
    """Requests and tokens per model provider per UTC day (router daily budgets)."""

    __tablename__ = "provider_usage"

    provider: Mapped[str] = mapped_column(String(100), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class SeriesCacheEntry(Base):
    """A fetched series, reused for 24 hours (adapters/cache.py)."""

    __tablename__ = "series_cache"
    __table_args__ = (UniqueConstraint("source", "code", "query_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(200), nullable=False)
    query_key: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 of filters
    geo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    filters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    rows: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    meta: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


EMBEDDING_DIM = 384  # BAAI/bge-small-en-v1.5 (holdsup.catalog.embed)


class Indicator(Base):
    """A curated catalog entry (packages/catalog), with its embedding for vector search."""

    __tablename__ = "indicators"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_code: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    geo_coverage: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    first_year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    related: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    filters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(20), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)


class Check(Base):
    """One submitted text and its result. Also the claim ledger: a finished check with a
    normalized text and an embedding can answer a later, identical claim."""

    __tablename__ = "checks"
    __table_args__ = (
        Index("ix_checks_normalized_text", "normalized_text"),
        Index("ix_checks_featured_created_at", "featured", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Set only when the result may answer later checks (ledger); null = not reusable.
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    providers: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # JSON documents: the CheckResult and the problem; Any because their shape is the API's.
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    cached_from: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("checks.id", ondelete="SET NULL"), nullable=True
    )
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ClaimRow(Base):
    """One extracted claim of a check, with its match, verdict and explanation."""

    __tablename__ = "claims"
    __table_args__ = (UniqueConstraint("check_id", "position"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    check_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("checks.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # ClaimSpec
    indicator_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verdict: Mapped[str] = mapped_column(String(40), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class OperationRow(Base):
    """One safe operation run for a claim, in order."""

    __tablename__ = "operations"
    __table_args__ = (UniqueConstraint("claim_id", "position"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # args + data points
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # value, series, flags
