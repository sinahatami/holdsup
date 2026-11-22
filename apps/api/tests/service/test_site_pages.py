"""Asking the site to drop a check's cached pages, against a fake site (no network)."""

from uuid import UUID

import httpx

from holdsup.service.site_pages import SitePages

ID = UUID("4c47ae9e-0c31-4fbd-a132-aa05dfdfc109")


def site(handler: httpx.MockTransport) -> SitePages:
    return SitePages(httpx.AsyncClient(transport=handler), "https://site.test/")


async def test_a_refresh_posts_to_the_check_and_succeeds_on_204() -> None:
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    pages = site(httpx.MockTransport(answer))
    assert await pages.refresh(ID)
    assert await pages.refresh(ID, gallery=True)
    assert [(r.method, str(r.url)) for r in seen] == [
        ("POST", f"https://site.test/api/checks/{ID}/refresh"),
        ("POST", f"https://site.test/api/checks/{ID}/refresh?gallery=1"),
    ]


async def test_a_refused_or_unreachable_refresh_is_false_never_raised() -> None:
    refused = site(httpx.MockTransport(lambda _: httpx.Response(404)))
    assert not await refused.refresh(ID)

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert not await site(httpx.MockTransport(down)).refresh(ID)
