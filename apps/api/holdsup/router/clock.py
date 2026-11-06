"""Injectable time source, so cool-downs and budgets are testable without sleeping."""

import time
from datetime import UTC, date, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float:
        """Seconds since the Unix epoch."""
        ...


class SystemClock:
    def now(self) -> float:
        return time.time()


def utc_day(ts: float) -> date:
    return datetime.fromtimestamp(ts, UTC).date()


def next_utc_midnight(ts: float) -> float:
    """Daily quotas are assumed to reset at 00:00 UTC."""
    day = utc_day(ts) + timedelta(days=1)
    return datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp()
