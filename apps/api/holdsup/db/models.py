"""ORM models. Import every model here so Alembic autogenerate sees it."""

from datetime import date

from sqlalchemy import BigInteger, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from holdsup.db.base import Base


class ProviderUsage(Base):
    """Requests and tokens per model provider per UTC day (router daily budgets)."""

    __tablename__ = "provider_usage"

    provider: Mapped[str] = mapped_column(String(100), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
