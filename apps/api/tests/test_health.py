from fastapi.testclient import TestClient

from holdsup.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_only_under_v1() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 404


def test_tolerances_are_the_ones_verdicts_use() -> None:
    from holdsup.verdict import load_tolerances

    body = TestClient(create_app()).get("/v1/tolerances").json()
    assert body == load_tolerances().model_dump(mode="json")
    assert body["framing_threshold"] == 0.7
    # Each kind of stated value carries its own gap; ranks allow none.
    assert set(body["values"]) == {
        "level", "level_rate", "absolute", "percent", "percentage_points", "ratio", "rank",
    }  # fmt: skip
    assert body["values"]["rank"]["absolute"] == 0
    assert set(body["max_period_gap"]) == {"annual", "semiannual", "quarterly", "monthly"}
