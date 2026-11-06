"""GET /v1/indicators?q= with a fake searcher (the real one needs Postgres + the model)."""

from fastapi.testclient import TestClient

from holdsup.catalog.index import IndicatorHit, InMemoryIndex
from holdsup.catalog.schema import load_catalog
from holdsup.main import create_app
from holdsup.routes.indicators import get_searcher
from tests.catalog.helpers import FIXTURE_CATALOG, HashEmbedder


class FakeSearcher:
    def __init__(self) -> None:
        self.embedder = HashEmbedder()
        self.index = InMemoryIndex.build(load_catalog(FIXTURE_CATALOG).indicators, self.embedder)
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, k: int) -> list[IndicatorHit]:
        self.calls.append((query, k))
        return self.index.search(self.embedder.embed([query])[0], k)


def client() -> tuple[TestClient, FakeSearcher]:
    app = create_app()
    searcher = FakeSearcher()
    app.dependency_overrides[get_searcher] = lambda: searcher
    return TestClient(app), searcher


def test_search_returns_ranked_hits() -> None:
    http, searcher = client()
    response = http.get("/v1/indicators", params={"q": "  life expectancy at birth ", "limit": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "  life expectancy at birth "
    assert len(body["results"]) == 3
    assert body["results"][0]["id"] == "life_expectancy"
    assert set(body["results"][0]) == {
        "id", "name", "source", "source_code", "unit", "frequency", "definition", "score",
    }  # fmt: skip
    assert searcher.calls == [("life expectancy at birth", 3)]


def test_default_limit_is_8() -> None:
    http, searcher = client()
    http.get("/v1/indicators", params={"q": "inflation"})
    assert searcher.calls == [("inflation", 8)]


def test_query_validation() -> None:
    http, _ = client()
    assert http.get("/v1/indicators").status_code == 422
    assert http.get("/v1/indicators", params={"q": "x"}).status_code == 422
    assert http.get("/v1/indicators", params={"q": "inflation", "limit": 50}).status_code == 422
