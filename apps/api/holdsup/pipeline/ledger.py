"""Step 1, the claim ledger: a claim checked before returns its stored result, no model call.

A hit needs the same claim, not merely similar text: the normalized text is equal, or its
embedding is close **and** it writes the same numbers and the same direction words. Without
that, "fell 12 points" would return the result for "fell 21 points".
"""

import re
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from holdsup.catalog.embed import Embedder
from holdsup.pipeline.extract import numbers_in

SIMILARITY_THRESHOLD = 0.95
MAX_AGE = timedelta(days=7)  # sources update; an old result may be stale

# Words that flip a claim's meaning while barely moving its embedding.
DIRECTION_WORDS = frozenset(
    {
        "rose",
        "rise",
        "rises",
        "risen",
        "rising",
        "up",
        "increase",
        "increased",
        "increases",
        "increasing",
        "grew",
        "grow",
        "grows",
        "grown",
        "growing",
        "higher",
        "high",
        "highest",
        "more",
        "most",
        "gained",
        "gain",
        "fell",
        "fall",
        "falls",
        "fallen",
        "falling",
        "down",
        "decrease",
        "decreased",
        "decreases",
        "decreasing",
        "shrank",
        "shrink",
        "shrinks",
        "shrunk",
        "dropped",
        "drop",
        "drops",
        "declined",
        "decline",
        "declines",
        "lower",
        "low",
        "lowest",
        "less",
        "least",
        "fewer",
        "lost",
        "not",
        "no",
        "never",
    }
)

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize_text(text: str) -> str:
    """Case, width, quotes, dashes and spacing folded; outer punctuation dropped."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES).casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .!?;:\"'")


def fingerprint(normalized: str) -> tuple[frozenset[float], frozenset[str]]:
    """What must match exactly for two texts to be the same claim."""
    words = set(re.findall(r"[a-z]+", normalized))
    return frozenset(numbers_in(normalized)), frozenset(words & DIRECTION_WORDS)


@dataclass(frozen=True)
class LedgerEntry:
    normalized: str
    embedding: list[float]
    result: dict[str, Any]  # the stored check result (JSON-able)
    created_at: datetime


@dataclass(frozen=True)
class LedgerHit:
    entry: LedgerEntry
    similarity: float  # 1.0 for an exact normalized match


class LedgerStore(Protocol):
    async def exact(self, normalized: str, since: datetime) -> LedgerEntry | None: ...

    async def nearest(
        self, embedding: list[float], since: datetime, k: int
    ) -> list[tuple[LedgerEntry, float]]: ...

    async def add(self, entry: LedgerEntry) -> None: ...


@dataclass
class InMemoryLedgerStore:
    entries: list[LedgerEntry] = field(default_factory=list)

    async def exact(self, normalized: str, since: datetime) -> LedgerEntry | None:
        for e in reversed(self.entries):
            if e.normalized == normalized and e.created_at >= since:
                return e
        return None

    async def nearest(
        self, embedding: list[float], since: datetime, k: int
    ) -> list[tuple[LedgerEntry, float]]:
        scored = [
            (e, sum(a * b for a, b in zip(e.embedding, embedding, strict=True)))
            for e in self.entries
            if e.created_at >= since
        ]
        return sorted(scored, key=lambda es: es[1], reverse=True)[:k]

    async def add(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class Ledger:
    store: LedgerStore
    embedder: Embedder
    threshold: float = SIMILARITY_THRESHOLD
    max_age: timedelta = MAX_AGE
    now: Callable[[], datetime] = _utcnow

    async def lookup(self, text: str) -> LedgerHit | None:
        normalized = normalize_text(text)
        since = self.now() - self.max_age
        if (entry := await self.store.exact(normalized, since)) is not None:
            return LedgerHit(entry, 1.0)
        mine = fingerprint(normalized)
        embedding = self.embedder.embed([normalized])[0]
        for entry, similarity in await self.store.nearest(embedding, since, k=5):
            if similarity < self.threshold:
                break
            if fingerprint(entry.normalized) == mine:
                return LedgerHit(entry, similarity)
        return None

    async def remember(self, text: str, result: dict[str, Any]) -> LedgerEntry:
        normalized = normalize_text(text)
        entry = LedgerEntry(
            normalized=normalized,
            embedding=self.embedder.embed([normalized])[0],
            result=result,
            created_at=self.now(),
        )
        await self.store.add(entry)
        return entry


async def check_with_ledger(
    ledger: Ledger, text: str, check: Callable[[str], Awaitable[dict[str, Any]]]
) -> tuple[dict[str, Any], LedgerHit | None]:
    """The stored result on a hit (no model call), else run `check` and store its result."""
    if (hit := await ledger.lookup(text)) is not None:
        return hit.entry.result, hit
    result = await check(text)
    await ledger.remember(text, result)
    return result, None
