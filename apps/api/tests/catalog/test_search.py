"""Vector search: alias → its indicator in the top 3, with the real local embedding model.

The model is never downloaded here (tests stay offline): run `make embed-model` once, or let
CI do it in a setup step. Without the model files these tests are skipped.
"""

import os
from collections.abc import Iterator

import pytest

from holdsup.catalog.embed import FastEmbedder, normalize
from holdsup.catalog.index import InMemoryIndex
from holdsup.catalog.schema import load_catalog
from tests.catalog.helpers import FIXTURE_CATALOG, HashEmbedder

CATALOG = load_catalog(FIXTURE_CATALOG)


@pytest.fixture(scope="module")
def embedder() -> Iterator[FastEmbedder]:
    cache = os.environ.get("FASTEMBED_CACHE_PATH")
    try:
        yield FastEmbedder(cache, local_only=True)
    except Exception as exc:  # noqa: BLE001  # any load failure means the model isn't cached
        pytest.skip(
            f"embedding model not available locally ({type(exc).__name__}); run make embed-model"
        )


@pytest.fixture(scope="module")
def index(embedder: FastEmbedder) -> InMemoryIndex:
    return InMemoryIndex.build(CATALOG.indicators, embedder)


ALIASES = [(spec.id, alias) for spec in CATALOG.indicators for alias in spec.aliases]


@pytest.mark.parametrize(("indicator_id", "alias"), ALIASES)
def test_every_alias_finds_its_indicator_in_top_3(
    embedder: FastEmbedder, index: InMemoryIndex, indicator_id: str, alias: str
) -> None:
    hits = index.search(embedder.embed([alias])[0], k=3)
    assert indicator_id in [h.id for h in hits]


@pytest.mark.parametrize(
    ("query", "indicator_id"),
    [
        ("young people out of work in Italy", "youth_unemployment_rate"),
        ("prices went up", "hicp_inflation"),
        ("tonnes of CO2 per person", "co2_per_capita"),
        ("Italians live longer than Germans", "life_expectancy"),
    ],
)
def test_paraphrases_not_in_catalog_text(
    embedder: FastEmbedder, index: InMemoryIndex, query: str, indicator_id: str
) -> None:
    hits = index.search(embedder.embed([query])[0], k=3)
    assert indicator_id in [h.id for h in hits]


def test_embeddings_are_normalized_and_384_dims(embedder: FastEmbedder) -> None:
    [v] = embedder.embed(["unemployment"])
    assert len(v) == 384
    assert sum(x * x for x in v) == pytest.approx(1.0, abs=1e-5)


def test_in_memory_index_orders_by_cosine_and_respects_k() -> None:
    embedder = HashEmbedder()
    index = InMemoryIndex.build(CATALOG.indicators, embedder)
    hits = index.search(embedder.embed(["Life expectancy at birth"])[0], k=2)
    assert hits[0].id == "life_expectancy"
    assert len(hits) == 2
    assert hits[0].score >= hits[1].score
    assert hits[0].source == "worldbank"


def test_normalize() -> None:
    assert normalize([3.0, 4.0]) == [0.6, 0.8]
    assert normalize([0.0, 0.0]) == [0.0, 0.0]
