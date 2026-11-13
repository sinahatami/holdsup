"""Test helpers: a small benchmark with both splits, a scripted search, a fake model client.

No network and no torch: the search is a fixed list, the router's client is a fake.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

from holdsup.catalog.schema import Catalog, load_catalog
from holdsup.router.client import ChatRequest, ChatResponse
from holdsup.router.config import ProviderConfig
from reranker import CATALOG
from reranker.benchmark import Claim, parse_claims

UNEMPLOYMENT = "unemployment_rate_monthly"
YOUTH = "youth_unemployment_rate_monthly"
DEBT = "government_debt_pct_gdp"
LIFE = "life_expectancy"  # covers every country
EUROSTAT_ONLY = (UNEMPLOYMENT, YOUTH, DEBT)  # cover Europe, not the US


def line(text_id: str, claims: Sequence[tuple[str, str | None, str]], split: str | None) -> str:
    row: dict[str, object] = {
        "id": text_id,
        "text": " ".join(q for q, _, _ in claims) + " (more words)",
        "claims": [
            {
                "quote": q,
                "indicator": i,
                "geo": g,
                "window": ["2020", "2020"],
                "expected": "supported",
                "justification": "x",
            }
            for q, i, g in claims
        ],
    }
    if split is not None:
        row["split"] = split
    return json.dumps(row)


BENCHMARK = [
    line("d1", [("Italy's unemployment rate was 8% in 2022", UNEMPLOYMENT, "IT")], "dev"),
    line(
        "d2",
        [
            ("Spain's youth unemployment rate was 30% in 2020", YOUTH, "ES"),
            ("Spain's debt was 120% of GDP in 2020", DEBT, "ES"),
        ],
        None,  # no split counts as dev
    ),
    line("d3", [("Italy had 100 unicorn companies in 2020", None, "IT")], "dev"),
    line("d4", [("Americans lived 77 years on average in 2021", LIFE, "US")], "dev"),
    line("t1", [("France's public debt was 99% of GDP in 2017", DEBT, "FR")], "test"),
    line("t2", [("Germany's unemployment rate was 3% in 2019", UNEMPLOYMENT, "DE")], "test"),
]


def claims() -> list[Claim]:
    return parse_claims(BENCHMARK)


def catalog() -> Catalog:
    return load_catalog(CATALOG)


@dataclass
class FixedSearch:
    """A search that answers every sentence with the same pool, and records what it was asked."""

    pool: Sequence[tuple[str, float]]
    asked: list[str] = field(default_factory=list)

    def __call__(self, sentences: Sequence[str]) -> list[list[tuple[str, float]]]:
        self.asked.extend(sentences)
        return [list(self.pool) for _ in sentences]


def json_reply(payload: object) -> ChatResponse:
    return ChatResponse(content=json.dumps(payload))


@dataclass
class FakeChat:
    """The router's client: replays `replies` in order (an exception is raised)."""

    replies: list[ChatResponse | Exception]
    requests: list[tuple[str, ChatRequest]] = field(default_factory=list)

    def has_key(self, provider: ProviderConfig) -> bool:
        return True

    async def complete(self, provider: ProviderConfig, request: ChatRequest) -> ChatResponse:
        self.requests.append((provider.name, request))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply
