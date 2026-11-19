"""Reading a page: every hop guarded and sent to the checked address, a deadline and a size cap.
A fake resolver and httpx's MockTransport stand in for DNS and the network."""

import asyncio
from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from holdsup.page import fetch
from holdsup.page.fetch import USER_AGENT, Unreadable, decode, fetch_page
from holdsup.page.guard import Blocked, Resolver

HTML = "<html><body><p>Unemployment fell to 7.7% in 2023.</p></body></html>"
HOSTS = {
    "news.example": ["93.184.215.14"],
    "v6.example": ["2606:2800:220:1::1"],
    "other.example": ["8.8.8.8"],
    "intranet.example": ["10.0.0.7"],
}


async def resolve(host: str, port: int) -> list[str]:
    if host not in HOSTS:
        raise OSError(f"unknown host {host}")
    return HOSTS[host]


Handler = Callable[[httpx.Request], httpx.Response]


async def read(link: str, handler: Handler, **kwargs: float) -> fetch.Fetched:
    return await fetch_page(link, resolve=resolve, transport=httpx.MockTransport(handler), **kwargs)


def page(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text=HTML, headers={"content-type": "text/html; charset=utf-8"})


async def test_the_request_goes_to_the_checked_address_with_the_sites_name() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return page(request)

    got = await read("https://news.example/jobs?id=4#top", handler)
    assert got == fetch.Fetched("https://news.example/jobs?id=4", HTML)
    (request,) = seen
    assert request.url.host == "93.184.215.14" and request.url.path == "/jobs"
    assert request.headers["host"] == "news.example"
    assert request.extensions["sni_hostname"] == "news.example"  # TLS checks the real name
    assert request.headers["user-agent"] == USER_AGENT
    assert "cookie" not in request.headers


async def test_ipv6_addresses_and_plain_http() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return page(request)

    await read("http://v6.example/a", handler)
    assert str(seen[0].url) == "http://[2606:2800:220:1::1]/a"
    assert "sni_hostname" not in seen[0].extensions


async def test_redirects_are_followed_and_each_hop_is_checked_again() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["host"] == "news.example":
            return httpx.Response(301, headers={"location": "https://other.example/story"})
        return page(request)

    got = await read("https://news.example/old", handler)
    assert got.url == "https://other.example/story"

    def to_intranet(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://intranet.example/admin"})

    with pytest.raises(Blocked, match="private or local"):
        await read("https://news.example/old", to_intranet)

    def to_metadata(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/"})

    with pytest.raises(Blocked):
        await fetch_page(
            "https://news.example/",
            resolve=_literal(resolve),
            transport=httpx.MockTransport(to_metadata),
        )

    def to_file(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "file:///etc/passwd"})

    with pytest.raises(Blocked, match="only http and https"):
        await read("https://news.example/", to_file)


def _literal(inner: Resolver) -> Resolver:
    """A resolver that, like the system's, returns a numeric host as it is."""

    async def resolve_literal(host: str, port: int) -> list[str]:
        return [host] if host[0].isdigit() else await inner(host, port)

    return resolve_literal


async def test_a_relative_redirect_and_too_many_redirects() -> None:
    def relative(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/end"})
        return page(request)

    assert (await read("https://news.example/start", relative)).url == "https://news.example/end"

    def loop(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "/again"})

    with pytest.raises(Unreadable, match="too many redirects"):
        await read("https://news.example/", loop)


@pytest.mark.parametrize(
    ("response", "why"),
    [
        (httpx.Response(404, text="gone"), r"error \(404\)"),
        (httpx.Response(302), r"error \(302\)"),  # a redirect without a Location
        (httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}),
         r"not a web page \(application/pdf\)"),
        (httpx.Response(200, text="x", headers={"content-type": "text/html",
                                                "content-length": str(fetch.MAX_BYTES + 1)}),
         "too large"),
    ],
)  # fmt: skip
async def test_pages_that_cannot_be_read(response: httpx.Response, why: str) -> None:
    with pytest.raises(Unreadable, match=why):
        await read("https://news.example/", lambda request: response)


async def test_a_page_with_no_content_type_is_tried_as_html() -> None:
    got = await read(
        "https://news.example/", lambda request: httpx.Response(200, content=b"<p>x</p>")
    )
    assert got.html == "<p>x</p>"


async def test_a_body_larger_than_the_cap_stops_the_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "MAX_BYTES", 10)

    class Chunks(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            for _ in range(5):
                yield b"<p>12345</p>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=Chunks(), headers={"content-type": "text/html"})

    with pytest.raises(Unreadable, match="too large"):
        await read("https://news.example/", handler)


async def test_a_body_that_breaks_off() -> None:
    class Broken(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b"<p>start"
            raise httpx.ReadError("reset")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=Broken(), headers={"content-type": "text/html"})

    with pytest.raises(Unreadable, match="part way"):
        await read("https://news.example/", handler)


async def test_unknown_sites_refused_connections_and_slow_sites() -> None:
    with pytest.raises(Unreadable, match="could not find"):
        await read("https://nowhere.example/", page)

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(Unreadable, match="could not connect"):
        await read("https://news.example/", refuse)

    async def slow(host: str, port: int) -> list[str]:
        await asyncio.sleep(1)
        return ["93.184.215.14"]

    with pytest.raises(Unreadable, match="too long"):
        await fetch_page("https://news.example/", resolve=slow, deadline_s=0.01)


async def test_blocked_links_never_reach_the_resolver() -> None:
    async def fail(host: str, port: int) -> list[str]:
        raise AssertionError("resolved a blocked link")

    with pytest.raises(Blocked):
        await fetch_page("https://user:pw@news.example/", resolve=fail)


def test_decoding_follows_the_header_then_the_meta_tag_then_utf8() -> None:
    latin = "<p>Città: 7,7 %</p>".encode("latin-1")
    assert decode(latin, "iso-8859-1") == "<p>Città: 7,7 %</p>"
    meta = b'<meta charset="windows-1252"><p>\x93quoted\x94</p>'
    assert decode(meta) == '<meta charset="windows-1252"><p>“quoted”</p>'
    assert decode(b"\xef\xbb\xbf<p>bom</p>", "latin-1") == "<p>bom</p>"
    assert decode("é".encode(), "no-such-charset") == "é"
    assert decode(b"<p>\xff</p>") == "<p>�</p>"
