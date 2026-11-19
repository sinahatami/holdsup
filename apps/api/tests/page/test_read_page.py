"""read_page: the fetch, the text and the excerpt together, and its three kinds of error."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

import holdsup.page as page_module
from holdsup.page import PageError, read_page
from holdsup.page.fetch import Fetched, Unreadable
from holdsup.page.guard import Blocked

ARTICLE = (Path(__file__).parents[1] / "fixtures" / "pages" / "article.html").read_text()


def fake_fetch(result: Fetched | Exception) -> Callable[[str], Awaitable[Fetched]]:
    async def fetch_page(link: str) -> Fetched:
        if isinstance(result, Exception):
            raise result
        return result

    return fetch_page


async def test_an_article_gives_its_paragraphs_with_figures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        page_module, "fetch_page", fake_fetch(Fetched("https://news.example/jobs", ARTICLE))
    )
    got = await read_page("https://news.example/jobs", 2_000)
    assert got.url == "https://news.example/jobs"
    assert got.title == "Youth unemployment in Italy has halved since 2015"
    assert got.text.startswith("Italy's youth unemployment rate fell from 40.3% in 2015")
    assert (got.used, got.found) == (3, 3)
    short = await read_page("https://news.example/jobs", 150)
    assert (short.used, short.found) == (1, 3) and len(short.text) <= 150


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (Blocked("That link points to a private or local address."), "not_allowed"),
        (Unreadable("The site answered with an error (404)."), "unreadable"),
        (
            Fetched("https://news.example/", "<p>Nothing to count here, only words.</p>"),
            "no_figures",
        ),
    ],
)
async def test_each_failure_has_its_kind_and_a_message_for_the_reader(
    monkeypatch: pytest.MonkeyPatch, error: Fetched | Exception, kind: str
) -> None:
    monkeypatch.setattr(page_module, "fetch_page", fake_fetch(error))
    with pytest.raises(PageError) as caught:
        await read_page("https://news.example/", 2_000)
    assert caught.value.kind == kind
    assert str(caught.value)
