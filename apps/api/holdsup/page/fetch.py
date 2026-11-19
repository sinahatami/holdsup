"""Reads one public web page: the guard's checks on every hop, a deadline and a size cap.

The client never follows redirects or proxies on its own: each hop is checked (guard.py),
resolved once, and requested from the address that was checked, with the site's name in the
Host header and in TLS (so the certificate is still verified against the name). No cookies
are kept and no connection is reused, so one site's connection never serves another's name.
"""

import asyncio
import codecs
import re
from dataclasses import dataclass

import httpx

from holdsup.page.guard import Resolver, checked_url, public_address, system_resolver

MAX_BYTES = 3_000_000  # of the page as served, after decompression
MAX_REDIRECTS = 5
DEADLINE_S = 12.0  # for the whole read, redirects included
USER_AGENT = "Mozilla/5.0 (compatible; HoldsUp claim checker)"
HTML_TYPES = ("text/html", "application/xhtml+xml")
_META_CHARSET = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_.:-]+)""", re.IGNORECASE
)


class Unreadable(Exception):
    """The page could not be read; the message says why, for the reader."""


@dataclass(frozen=True)
class Fetched:
    url: str  # the page's address after any redirects, without a #fragment
    html: str


async def fetch_page(
    link: str,
    *,
    resolve: Resolver = system_resolver,
    transport: httpx.AsyncBaseTransport | None = None,
    deadline_s: float = DEADLINE_S,
) -> Fetched:
    """The HTML at `link`. Raises Blocked (guard.py) for a link HoldsUp will not open and
    Unreadable for one it could not read."""
    url = checked_url(link)
    try:
        async with asyncio.timeout(deadline_s):
            return await _follow(url, resolve, transport, deadline_s)
    except TimeoutError as exc:
        raise Unreadable("The site took too long to answer.") from exc


async def _follow(
    url: httpx.URL,
    resolve: Resolver,
    transport: httpx.AsyncBaseTransport | None,
    deadline_s: float,
) -> Fetched:
    async with httpx.AsyncClient(
        transport=transport,
        trust_env=False,  # no proxy from the environment: the checked address is the one used
        follow_redirects=False,
        timeout=httpx.Timeout(deadline_s),
        limits=httpx.Limits(max_keepalive_connections=0),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9",
            "Accept-Language": "en",
            "Accept-Encoding": "gzip, deflate",
        },
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            url = checked_url(url)
            response = await _request(client, url, resolve)
            try:
                location = response.headers.get("location")
                if response.is_redirect and location:
                    url = url.join(location)
                    continue
                return Fetched(str(url.copy_with(fragment=None)), await _html(response))
            finally:
                await response.aclose()
    raise Unreadable("The page sent HoldsUp through too many redirects.")


async def _request(client: httpx.AsyncClient, url: httpx.URL, resolve: Resolver) -> httpx.Response:
    try:
        address = await public_address(url, resolve)
    except OSError as exc:
        raise Unreadable("HoldsUp could not find that site.") from exc
    host = url.raw_host.decode("ascii")
    request = client.build_request(
        "GET",
        url.copy_with(host=address, fragment=None),
        headers={"Host": url.netloc.decode("ascii")},
        extensions={"sni_hostname": host} if url.scheme == "https" else {},
    )
    try:
        return await client.send(request, stream=True)
    except httpx.HTTPError as exc:
        raise Unreadable("HoldsUp could not connect to that site.") from exc


async def _html(response: httpx.Response) -> str:
    if response.status_code != 200:
        raise Unreadable(f"The site answered with an error ({response.status_code}).")
    media = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media and media not in HTML_TYPES:
        raise Unreadable(f"That link is not a web page ({media}). HoldsUp reads HTML articles.")
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BYTES:
        raise Unreadable("The page is too large to read.")
    body = bytearray()
    try:
        async for chunk in response.aiter_bytes():
            body += chunk
            if len(body) > MAX_BYTES:
                raise Unreadable("The page is too large to read.")
    except httpx.HTTPError as exc:
        raise Unreadable("The site stopped sending the page part way.") from exc
    return decode(bytes(body), response.charset_encoding)


def decode(body: bytes, declared: str | None = None) -> str:
    """The page as text: in the charset the response declares, else the one a <meta> tag
    names, else UTF-8. Bytes that do not decode become U+FFFD instead of failing the read."""
    if body.startswith(codecs.BOM_UTF8):
        return body[len(codecs.BOM_UTF8) :].decode("utf-8", errors="replace")
    meta = _META_CHARSET.search(body[:4096])
    for name in (declared, meta.group(1).decode("ascii") if meta else None):
        if not name:
            continue
        try:
            return body.decode(codecs.lookup(name).name, errors="replace")
        except LookupError:
            continue
    return body.decode("utf-8", errors="replace")
