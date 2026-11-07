"""Place names to claim codes: names, demonyms and short forms, and what stays unknown."""

from collections import defaultdict

import pytest

from holdsup.geo import ISO3
from holdsup.places import _NAMES, BY_NAME, GEO_GROUPS, is_name, place_code


def test_every_code_in_the_table_is_a_real_code() -> None:
    assert all(code in ISO3 or code in GEO_GROUPS for code in _NAMES)


def test_no_name_stands_for_two_places() -> None:
    from holdsup.places import _key

    seen: dict[str, set[str]] = defaultdict(set)
    for code, names in _NAMES.items():
        for name in names:
            seen[_key(name)].add(code)
    assert {k: v for k, v in seen.items() if len(v) > 1} == {}
    assert len(BY_NAME) == len(seen)


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("IT", "IT"), ("it", "IT"), (" gb ", "GB"), ("UK", "GB"), ("EL", "GR"), ("EU27_2020", "EU"),
        ("WLD", "WORLD"), ("G7", "G7"), ("ITA", "IT"), ("USA", "US"), ("DEU", "DE"),
        ("Italy", "IT"), ("italy", "IT"), ("ITALY", "IT"), ("Italian", "IT"), ("the Italians", "IT"),
        ("the UK", "GB"), ("U.K.", "GB"), ("Britain", "GB"), ("Great Britain", "GB"),
        ("British", "GB"), ("United Kingdom", "GB"), ("the United Kingdom", "GB"),
        ("US", "US"), ("U.S.", "US"), ("the US", "US"), ("America", "US"), ("American", "US"),
        ("United States", "US"), ("the United States of America", "US"),
        ("Germany", "DE"), ("German", "DE"), ("France", "FR"), ("French", "FR"),
        ("Greece", "GR"), ("Holland", "NL"), ("the Netherlands", "NL"), ("Dutch", "NL"),
        ("Türkiye", "TR"), ("Turkey", "TR"), ("Czech Republic", "CZ"), ("South Korea", "KR"),
        ("South Africa", "ZA"), ("South African", "ZA"), ("Russia", "RU"), ("China", "CN"),
        ("Eurozone", "EA"), ("the euro area", "EA"), ("euro-zone", "EA"), ("European Union", "EU"),
        ("the EU", "EU"), ("the world", "WORLD"), ("global", "WORLD"), ("OECD", "OECD"),
        ("  Italy  ", "IT"),
    ],
)  # fmt: skip
def test_place_code(raw: str, code: str) -> None:
    assert place_code(raw) == code


@pytest.mark.parametrize(
    "raw",
    ["Europe", "Atlantis", "Korea", "Congo", "Georgia", "XX", "", "   ", "Italy and France", None],
)
def test_unknown_or_ambiguous_places_stay_unknown(raw: str | None) -> None:
    assert place_code(raw) is None


def test_is_name_tells_codes_from_names() -> None:
    assert [is_name(t) for t in ("IT", "uk", "ITA", "EU27", "Italy", "the UK", "Eurozone")] == [
        False, False, False, False, True, True, True,
    ]  # fmt: skip
