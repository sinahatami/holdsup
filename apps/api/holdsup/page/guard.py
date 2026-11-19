"""Which links HoldsUp opens: public web pages only.

A link names a host; the server resolves it and connects. Without a guard, a link to
`localhost`, a private network or a cloud metadata address (169.254.169.254) would make the
server read something only it can reach (server-side request forgery). So:

- only `http` and `https`, on their usual ports (80, 443), with no user name or password;
- every address the host resolves to must be public; one private address blocks the link;
- the connection goes to the address that was checked, never to a second lookup, so a name
  that resolves differently a moment later (DNS rebinding) cannot slip past;
- each redirect is checked again the same way (fetch.py).
"""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable

import httpx

PORTS = {"http": 80, "https": 443}
MAX_LINK = 2_000  # characters, the same cap as pasted text
_NAT64 = ipaddress.ip_network("64:ff9b::/96")  # an IPv4 address inside an IPv6 one

# host, port → every address the host resolves to.
Resolver = Callable[[str, int], Awaitable[list[str]]]


class Blocked(Exception):
    """A link HoldsUp will not open; the message says why, for the reader."""


def as_link(text: str) -> str | None:
    """The link when `text` is nothing but one web address, else None (it is text to check).
    A bare `www.` address is read as https."""
    s = text.strip()
    if not s or len(s) > MAX_LINK or any(c.isspace() for c in s):
        return None
    lower = s.lower()
    if lower.startswith(("http://", "https://")):
        return s
    if lower.startswith("www.") and "." in s[4:]:
        return f"https://{s}"
    return None


def checked_url(link: str | httpx.URL) -> httpx.URL:
    """`link` as a URL HoldsUp may open, or Blocked."""
    try:
        url = httpx.URL(link)
    except httpx.InvalidURL as exc:
        raise Blocked("That does not look like a web address.") from exc
    if url.scheme not in PORTS:
        raise Blocked("HoldsUp opens only http and https links.")
    if not url.raw_host:
        raise Blocked("That link has no site name in it.")
    if url.userinfo:
        raise Blocked("HoldsUp does not open links that carry a user name or password.")
    if url.port not in (None, PORTS[url.scheme]):
        raise Blocked("HoldsUp opens links on the usual web ports only (80 and 443).")
    return url


def is_public(address: str) -> bool:
    """True for an address anyone on the internet can reach; False for loopback, private,
    link-local, shared (100.64/10), reserved, multicast and unparsable ones. An IPv4 address
    carried inside IPv6 (mapped or NAT64) is judged as that IPv4 address."""
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])  # drop an IPv6 zone ("%eth0")
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        elif ip in _NAT64:
            ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip.is_global and not ip.is_multicast


async def system_resolver(host: str, port: int) -> list[str]:
    """Every address the system resolver gives for `host` (async: no blocking lookup)."""
    infos = await asyncio.get_running_loop().getaddrinfo(
        host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
    )
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


async def public_address(url: httpx.URL, resolve: Resolver) -> str:
    """The address to connect to for `url`: the first it resolves to, once every one of them
    is public. Raises Blocked otherwise, and OSError when the name does not resolve."""
    host = url.raw_host.decode("ascii")
    addresses = await resolve(host, url.port or PORTS[url.scheme])
    if not addresses:
        raise OSError(f"{host} has no address")
    if not all(is_public(a) for a in addresses):
        raise Blocked(
            "That link points to a private or local address, which HoldsUp does not open."
        )
    return addresses[0]
