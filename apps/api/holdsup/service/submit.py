"""Text or a link in, a started check out: what `POST /v1/checks` and the Telegram bot share.

A link's page is read before the check starts, so a page with nothing to check is a plain
error (a ProblemError) rather than a failed check; its excerpt is then checked, and cached,
like pasted text.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from holdsup.page import PageError, PageReader, as_link
from holdsup.problems import (
    ProblemError,
    link_not_allowed,
    no_figures,
    page_unreadable,
    pages_limited,
)
from holdsup.service.ratelimit import RateLimiter
from holdsup.service.runner import CheckRunner, Submitted
from holdsup.service.store import PageSource

MAX_TEXT = 2_000  # characters, after trimming whitespace

_PAGE_PROBLEMS = {
    "not_allowed": link_not_allowed,
    "unreadable": page_unreadable,
    "no_figures": no_figures,
}


@dataclass(frozen=True)
class Submitter:
    runner: CheckRunner
    pages: PageReader
    page_limiter: RateLimiter

    async def submit(self, text: str, client: str) -> Submitted:
        """Start a check of `text` for `client` (the key its limits count). Raises
        ProblemError when a limit is reached or a link gives nothing to check."""
        link = as_link(text)
        if link is None:
            return await self.runner.submit(text, client)
        wait = self.page_limiter.hit(client)
        if wait is not None:
            raise ProblemError(pages_limited(wait))
        try:
            page = await self.pages(link, MAX_TEXT)
        except PageError as exc:
            raise ProblemError(_PAGE_PROBLEMS[exc.kind](str(exc))) from exc
        source = PageSource(
            url=page.url, title=page.title, read_at=datetime.now(UTC), used=page.used,
            found=page.found,
        )  # fmt: skip
        return await self.runner.submit(page.text, client, page=source)
