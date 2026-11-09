"""GET /v1/indicators?q= with a fake search (the real one needs Postgres + the model)."""

from fastapi.testclient import TestClient

from holdsup.catalog.index import IndicatorHit, InMemoryIndex
from holdsup.catalog.schema import Theme, load_catalog
from holdsup.main import create_app
from holdsup.routes.deps import get_catalog_search
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
    app.dependency_overrides[get_catalog_search] = lambda: searcher.search
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


def test_catalog_lists_everything_a_to_z() -> None:
    from holdsup.routes.deps import get_catalog

    app = create_app()
    catalog = load_catalog(FIXTURE_CATALOG)
    app.dependency_overrides[get_catalog] = lambda: catalog
    body = TestClient(app).get("/v1/catalog").json()
    names = [i["name"] for i in body["indicators"]]
    assert body["version"] == catalog.version
    assert names == sorted(names, key=str.casefold) and len(names) == len(catalog.indicators)
    assert set(body["indicators"][0]) == {
        "id", "name", "theme", "definition", "unit", "source", "frequency", "first_year", "last_year",
        "source_code", "aliases", "countries", "groups", "all_countries",
    }  # fmt: skip
    assert {i["theme"] for i in body["indicators"]} <= {t.value for t in Theme}


def test_catalog_says_which_places_each_entry_covers() -> None:
    from holdsup.routes.deps import get_catalog

    app = create_app()
    catalog = load_catalog(FIXTURE_CATALOG)
    app.dependency_overrides[get_catalog] = lambda: catalog
    body = TestClient(app).get("/v1/catalog").json()
    by_id = {i["id"]: i for i in body["indicators"]}
    for spec in catalog.indicators:
        entry = by_id[spec.id]
        assert entry["source_code"] == spec.source_code
        assert entry["aliases"] == list(spec.aliases)
        # Countries are ISO codes; the groups are never mistaken for countries.
        assert all(len(c) == 2 and c not in {"EU", "EA"} for c in entry["countries"])
        assert set(entry["groups"]) <= {"EU", "EA", "WORLD"}
