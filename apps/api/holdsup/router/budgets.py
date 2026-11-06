"""Request budgets: per-minute counts in memory, per-day counts in a durable store.

A provider is skipped once it reaches 90% of a published limit, instead of waiting for 429s.
"""

import math
from collections import defaultdict, deque
from datetime import date
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from holdsup.db.models import ProviderUsage
from holdsup.router.clock import utc_day
from holdsup.router.config import ProviderConfig

BUDGET_FRACTION = 0.9
WINDOW_S = 60.0


def budget_cap(limit: int) -> int:
    """Largest request count we allow ourselves: 90% of the limit, at least 1."""
    return max(1, math.floor(limit * BUDGET_FRACTION))


class UsageStore(Protocol):
    async def requests_on(self, provider: str, day: date) -> int: ...

    async def record(self, provider: str, day: date, tokens: int) -> None: ...

    async def add_tokens(self, provider: str, day: date, tokens: int) -> None: ...


class InMemoryUsageStore:
    """For tests and offline scripts. Counts are lost on restart."""

    def __init__(self) -> None:
        self.requests: dict[tuple[str, date], int] = defaultdict(int)
        self.tokens: dict[tuple[str, date], int] = defaultdict(int)

    async def requests_on(self, provider: str, day: date) -> int:
        return self.requests[(provider, day)]

    async def record(self, provider: str, day: date, tokens: int) -> None:
        self.requests[(provider, day)] += 1
        self.tokens[(provider, day)] += tokens

    async def add_tokens(self, provider: str, day: date, tokens: int) -> None:
        self.tokens[(provider, day)] += tokens


class SqlUsageStore:
    """Per-day counts in the `provider_usage` table, so they survive restarts."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def requests_on(self, provider: str, day: date) -> int:
        async with self._sessionmaker() as session:
            stmt = select(ProviderUsage.requests).where(
                ProviderUsage.provider == provider, ProviderUsage.day == day
            )
            return (await session.scalar(stmt)) or 0

    async def record(self, provider: str, day: date, tokens: int) -> None:
        stmt = insert(ProviderUsage).values(provider=provider, day=day, requests=1, tokens=tokens)
        stmt = stmt.on_conflict_do_update(
            index_elements=[ProviderUsage.provider, ProviderUsage.day],
            set_={
                "requests": ProviderUsage.requests + 1,
                "tokens": ProviderUsage.tokens + stmt.excluded.tokens,
            },
        )
        async with self._sessionmaker() as session, session.begin():
            await session.execute(stmt)

    async def add_tokens(self, provider: str, day: date, tokens: int) -> None:
        stmt = (
            update(ProviderUsage)
            .where(ProviderUsage.provider == provider, ProviderUsage.day == day)
            .values(tokens=ProviderUsage.tokens + tokens)
        )
        async with self._sessionmaker() as session, session.begin():
            await session.execute(stmt)


class Budgets:
    def __init__(self, store: UsageStore) -> None:
        self._store = store
        self._minute: dict[str, deque[float]] = defaultdict(deque)

    def _minute_count(self, provider: str, now: float) -> int:
        window = self._minute[provider]
        while window and window[0] <= now - WINDOW_S:
            window.popleft()
        return len(window)

    def minute_wait_s(self, provider: ProviderConfig, now: float) -> float:
        """Seconds until the per-minute budget frees a slot (0 if one is free now)."""
        if self._minute_count(provider.name, now) < budget_cap(provider.limits.requests_per_minute):
            return 0.0
        return self._minute[provider.name][0] + WINDOW_S - now

    async def day_exhausted(self, provider: ProviderConfig, now: float) -> bool:
        per_day = provider.limits.requests_per_day
        if per_day is None:
            return False
        used = await self._store.requests_on(provider.name, utc_day(now))
        return used >= budget_cap(per_day)

    async def remaining_today(self, provider: ProviderConfig, now: float) -> int | None:
        """For the /status page (P3.7)."""
        per_day = provider.limits.requests_per_day
        if per_day is None:
            return None
        used = await self._store.requests_on(provider.name, utc_day(now))
        return max(0, budget_cap(per_day) - used)

    async def record(self, provider: ProviderConfig, now: float, tokens: int = 0) -> None:
        """Count one request (successful or not: providers count attempts)."""
        self._minute[provider.name].append(now)
        await self._store.record(provider.name, utc_day(now), tokens)

    async def add_tokens(self, provider: ProviderConfig, now: float, tokens: int) -> None:
        """Add the tokens of a finished call to today's row."""
        if tokens:
            await self._store.add_tokens(provider.name, utc_day(now), tokens)
