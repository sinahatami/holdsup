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
