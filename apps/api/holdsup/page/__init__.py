"""Article links (stretch S3): read a public web page and keep the paragraphs with figures.

`read_page` is the one entry point: guard and fetch (guard.py, fetch.py), the readable text
(text.py), then the part to check (excerpt.py). The excerpt is checked like pasted text, so
it is data for the models, never instructions, exactly as pasted text is.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

import structlog

from holdsup.page.excerpt import excerpt
from holdsup.page.fetch import Unreadable, fetch_page
from holdsup.page.guard import Blocked, as_link
from holdsup.page.text import read_html

__all__ = ["PageError", "PageErrorKind", "PageExcerpt", "PageReader", "as_link", "read_page"]

log = structlog.get_logger(__name__)

PageErrorKind = Literal["not_allowed", "unreadable", "no_figures"]


@dataclass(frozen=True)
class PageExcerpt:
    url: str  # after redirects
    title: str | None
    text: str  # what is checked
    used: int  # passages with figures in `text`
    found: int  # passages with figures on the page


class PageError(Exception):
    """A link that gave nothing to check; the message says why, for the reader."""

    def __init__(self, kind: PageErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


# link, the longest text to check → the excerpt.
PageReader = Callable[[str, int], Awaitable[PageExcerpt]]


async def read_page(link: str, limit: int) -> PageExcerpt:
    """The paragraphs with figures at `link`, at most `limit` characters. Raises PageError."""
    try:
        fetched = await fetch_page(link)
    except Blocked as exc:
        raise PageError("not_allowed", str(exc)) from exc
    except Unreadable as exc:
        raise PageError("unreadable", str(exc)) from exc
    # Parsing a large page is a few hundred milliseconds of CPU: off the event loop.
    page = await asyncio.to_thread(read_html, fetched.html)
    cut = excerpt(page.paragraphs, limit)
    log.info("page_read", paragraphs=len(page.paragraphs), used=cut.used, found=cut.found)
    if not cut.used:
        raise PageError(
            "no_figures",
            "HoldsUp read the page but found no sentence with a figure to check. "
            "Paste the sentence you want checked instead.",
        )
    return PageExcerpt(fetched.url, page.title, cut.text, cut.used, cut.found)
