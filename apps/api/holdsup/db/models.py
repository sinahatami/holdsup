"""ORM models. Import every model here so Alembic autogenerate sees it."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, Text, UniqueConstraint
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
