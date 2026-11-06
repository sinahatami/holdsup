"""Model filtering in the list-models script (the real run needs keys and network)."""

import pytest
from scripts.list_models import _on_domain, _visible

from holdsup.router.client import ModelInfo
from holdsup.router.config import ProviderConfig
from tests.router.fakes import provider


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://generativelanguage.googleapis.com/v1beta/openai/", True),
        ("https://googleapis.com/v1", True),
        ("https://googleapis.com.evil.example/v1", False),
        ("https://evil.example/googleapis.com/v1", False),
        ("https://notgoogleapis.com/v1", False),
    ],
)
def test_on_domain_matches_the_host_only(url: str, expected: bool) -> None:
    assert _on_domain(url, "googleapis.com") is expected


def cfg(base_url: str) -> ProviderConfig:
    return ProviderConfig.model_validate(provider("p", base_url=base_url))


def test_visible_filters_per_provider() -> None:
    openrouter = cfg("https://openrouter.ai/api/v1")
    assert _visible(openrouter, ModelInfo("a/b:free"), show_all=False)
    assert not _visible(openrouter, ModelInfo("a/b"), show_all=False)
    assert _visible(openrouter, ModelInfo("a/b"), show_all=True)
    gemini = cfg("https://generativelanguage.googleapis.com/v1beta/openai/")
    assert _visible(gemini, ModelInfo("gemini-3.5-flash"), show_all=False)
    assert not _visible(gemini, ModelInfo("gemini-embedding-001"), show_all=False)
    assert _visible(cfg("https://api.groq.com/openai/v1"), ModelInfo("x"), show_all=False)
