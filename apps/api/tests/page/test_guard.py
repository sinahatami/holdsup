"""The SSRF guard: which links are opened, and which addresses count as public."""

import ipaddress

import httpx
import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.page.guard import (
    Blocked,
    Resolver,
    as_link,
    checked_url,
    is_public,
    public_address,
    system_resolver,
)


@pytest.mark.parametrize(
    ("text", "link"),
    [
        ("https://example.com/news/jobs", "https://example.com/news/jobs"),
        ("  HTTP://Example.com/a?b=1  ", "HTTP://Example.com/a?b=1"),
        ("www.example.com/story", "https://www.example.com/story"),
        ("Italy's unemployment fell to 7.7%.", None),
        ("see https://example.com for more", None),  # text with a link in it is text
        ("www.", None),
        ("ftp://example.com/file", None),
        ("", None),
        ("https://example.com/" + "x" * 2_000, None),
    ],
)
def test_only_a_text_that_is_one_web_address_is_a_link(text: str, link: str | None) -> None:
    assert as_link(text) == link


@pytest.mark.parametrize(
    ("link", "why"),
    [
        ("file:///etc/passwd", "only http and https"),
        ("gopher://example.com/", "only http and https"),
        ("http:///nohost", "no site name"),
        ("https://user:secret@example.com/", "user name or password"),
        ("https://example.com:8443/", "usual web ports"),
        ("http://example.com:22/", "usual web ports"),
        ("http://example.com:99999/", "usual web ports"),
        ("http://[::1/", "does not look like a web address"),
    ],
)
def test_links_that_are_not_plain_public_web_pages_are_blocked(link: str, why: str) -> None:
    with pytest.raises(Blocked, match=why):
        checked_url(link)


def test_the_usual_ports_written_out_are_fine() -> None:
    assert checked_url("https://example.com:443/a").raw_host == b"example.com"
    assert checked_url("http://example.com:80/a").port is None


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1", "10.1.2.3", "172.16.0.1", "192.168.1.1", "169.254.169.254",
        "0.0.0.0",  # noqa: S104 (an address to reject, not one to bind)
        "100.64.0.1", "198.18.0.1", "224.0.0.1", "255.255.255.255", "::1", "::", "fe80::1%eth0",
        "fc00::1", "fd12:3456::1", "::ffff:127.0.0.1", "::ffff:10.0.0.1", "64:ff9b::7f00:1",
        "64:ff9b::a00:1", "ff02::1", "not-an-address", "",
    ],
)  # fmt: skip
def test_private_local_reserved_and_multicast_addresses_are_not_public(address: str) -> None:
    assert not is_public(address)


@pytest.mark.parametrize(
    "address",
    ["93.184.215.14", "8.8.8.8", "2001:4860:4860::8888", "::ffff:8.8.8.8", "64:ff9b::808:808"],
)
def test_internet_addresses_are_public(address: str) -> None:
    assert is_public(address)


@given(st.ip_addresses(v=4))
def test_an_ipv4_address_inside_ipv6_is_judged_as_itself(ip: ipaddress.IPv4Address) -> None:
    nat64 = ipaddress.IPv6Address(int(ipaddress.IPv6Address("64:ff9b::")) | int(ip))
    assert is_public(f"::ffff:{ip}") == is_public(str(ip)) == is_public(str(nat64))


def _resolver(table: dict[str, list[str]]) -> Resolver:
    async def resolve(host: str, port: int) -> list[str]:
        return table[host]

    return resolve


async def test_every_address_of_a_host_must_be_public() -> None:
    resolve = _resolver(
        {"good.example": ["93.184.215.14", "2606:2800::1"], "mixed.example": ["93.184.215.14", "10.0.0.5"],
         "none.example": []}
    )  # fmt: skip
    assert await public_address(httpx.URL("https://good.example/"), resolve) == "93.184.215.14"
    with pytest.raises(Blocked, match="private or local"):
        await public_address(httpx.URL("https://mixed.example/"), resolve)
    with pytest.raises(OSError, match="no address"):
        await public_address(httpx.URL("https://none.example/"), resolve)


async def test_the_system_resolver_reads_literal_addresses_without_a_lookup() -> None:
    # A numeric host needs no DNS, so this stays off the network.
    assert await system_resolver("127.0.0.1", 80) == ["127.0.0.1"]
    assert await system_resolver("2130706433", 80) == ["127.0.0.1"]  # 127.0.0.1 as one number
