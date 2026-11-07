"""Claim ledger: exact and near-duplicate hits, with no model call on a hit."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from holdsup.pipeline.extract import extract_claims
from holdsup.pipeline.ledger import (
    InMemoryLedgerStore,
    Ledger,
    LedgerEntry,
    check_with_ledger,
    fingerprint,
    normalize_text,
)
from holdsup.router import Router
from holdsup.router.client import ChatResponse
from tests.catalog.helpers import HashEmbedder
from tests.router.fakes import FakeClient, FakeClock, config, provider

T0 = datetime(2026, 11, 7, 12, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.t = T0

    def __call__(self) -> datetime:
        return self.t


def ledger(threshold: float = 0.95, clock: Clock | None = None) -> Ledger:
    return Ledger(InMemoryLedgerStore(), HashEmbedder(), threshold, now=clock or Clock())


def test_normalize_text() -> None:
    assert normalize_text("  Italy’s  youth\nunemployment — HALVED!  ") == (
        "italy's youth unemployment - halved"
    )


def test_fingerprint() -> None:
    assert fingerprint("unemployment fell 12 points since 2015") == (
        frozenset({12.0, 2015.0}),
        frozenset({"fell"}),
    )


# --- the task's test: a repeated claim makes zero model calls --------------------------------

TEXT = "Italy's youth unemployment fell 12 points since 2014."
EXTRACTION: dict[str, Any] = {
    "speaker": None,
    "said_on": None,
    "claims": [
        {
            "quote": "Italy's youth unemployment fell 12 points since 2014",
            "indicator_phrase": "youth unemployment",
            "geo": "IT",
            "geo_named": True,
            "peers": [],
            "start": "2014",
            "start_named": True,
            "end": "latest",
            "lookback": None,
            "office": None,
            "assertion": {
                "type": "percentage_points",
                "value": 12,
                "direction": "down",
                "unit": "points",
                "start_value": None,
                "end_value": None,
            },
        }
    ],
}


async def test_a_repeated_claim_hits_the_ledger_with_zero_model_calls() -> None:
    client = FakeClient(default=ChatResponse(content=json.dumps(EXTRACTION)))
    router = Router(config(provider("fake"), steps={"extract": ["fake"]}), client,
                    clock=FakeClock())  # fmt: skip

    async def check(text: str) -> dict[str, Any]:
        result = await extract_claims(router, text)
        return {"claims": [c.model_dump(mode="json") for c in result.claims]}

    store = ledger()
    first, hit = await check_with_ledger(store, TEXT, check)
    assert hit is None and len(client.calls) == 1
    assert first["claims"][0]["indicator_phrase"] == "youth unemployment"

    again, hit = await check_with_ledger(store, "  italy's YOUTH unemployment fell 12 points "
                                         "since 2014 ", check)  # fmt: skip
    assert hit is not None and hit.similarity == 1.0
    assert again == first
    assert len(client.calls) == 1  # no model call on the hit

    # Different numbers are a different claim, however similar the text.
    _, hit = await check_with_ledger(store, TEXT.replace("12", "21"), check)
    assert hit is None and len(client.calls) == 2


# --- near duplicates -------------------------------------------------------------------------


async def test_near_duplicate_with_the_same_numbers_and_direction_hits() -> None:
    store = ledger(threshold=0.8)
    await store.remember("Youth unemployment in Italy fell 12 points since 2014", {"v": 1})
    hit = await store.lookup("Since 2014 youth unemployment in Italy has fell 12 points")
    assert hit is not None and 0.8 <= hit.similarity < 1.0
    assert hit.entry.result == {"v": 1}


async def test_near_duplicate_with_another_direction_misses() -> None:
    store = ledger(threshold=0.8)
    await store.remember("Youth unemployment in Italy fell 12 points since 2014", {"v": 1})
    assert await store.lookup("Youth unemployment in Italy rose 12 points since 2014") is None


async def test_below_the_threshold_misses() -> None:
    store = ledger(threshold=0.99)
    await store.remember("Youth unemployment in Italy fell 12 points since 2014", {"v": 1})
    assert await store.lookup("Since 2014 youth unemployment in Italy has fell 12 points") is None


async def test_old_entries_are_ignored() -> None:
    clock = Clock()
    store = ledger(clock=clock)
    await store.remember(TEXT, {"v": 1})
    clock.t = T0 + timedelta(days=8)
    assert await store.lookup(TEXT) is None
    await store.remember(TEXT, {"v": 2})
    hit = await store.lookup(TEXT)
    assert hit is not None and hit.entry.result == {"v": 2}


async def test_in_memory_store_nearest_is_ranked_and_limited() -> None:
    s = InMemoryLedgerStore()

    def entry(name: str, vector: Sequence[float]) -> LedgerEntry:
        return LedgerEntry(name, list(vector), {}, T0)

    for e in (entry("a", [1, 0]), entry("b", [0.6, 0.8]), entry("c", [0, 1])):
        await s.add(e)
    ranked = await s.nearest([1.0, 0.0], T0, k=2)
    assert [(e.normalized, round(sim, 2)) for e, sim in ranked] == [("a", 1.0), ("b", 0.6)]
    assert await s.exact("b", T0 + timedelta(seconds=1)) is None


async def test_default_clock_is_utc_now() -> None:
    store = Ledger(InMemoryLedgerStore(), HashEmbedder())
    entry = await store.remember(TEXT, {})
    assert entry.created_at.tzinfo is UTC
    assert abs(datetime.now(UTC) - entry.created_at) < timedelta(minutes=1)
