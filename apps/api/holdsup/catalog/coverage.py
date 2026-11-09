"""Which places a catalog entry covers, from its `geo_coverage` labels.

Geo codes are the claim spec's: ISO 3166-1 alpha-2 (GB, GR) plus EU, EA, WORLD. Matching
drops candidates that cannot cover the claim's place before the model picks
(docs/notes.md "P1.12 Pivot test review", item 1).
"""

import re
from collections.abc import Iterable

# fmt: off
EU_MEMBERS = frozenset({
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU",
    "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
})
# fmt: on
EFTA = frozenset({"CH", "IS", "LI", "NO"})

# label -> the codes it covers; "*" = every country code (not aggregates)
LABELS: dict[str, frozenset[str]] = {
    "All countries": frozenset({"*"}),
    "EU member states": EU_MEMBERS,
    "EFTA countries": EFTA,
    "EU27_2020": frozenset({"EU"}),
    "EA": frozenset({"EA"}),
    "WLD": frozenset({"WORLD"}),
    "OWID_WRL": frozenset({"WORLD"}),
    # Regional series: claims about a region carry the country's code.
    "NUTS 1 and NUTS 2 regions": EU_MEMBERS,
}
_COUNTRY = re.compile(r"[A-Z]{2}")
AGGREGATES = frozenset({"EU", "EA", "WORLD", "G7", "G20", "OECD"})  # not countries


class UnknownCoverageLabel(ValueError):
    pass


def covered_codes(labels: Iterable[str]) -> frozenset[str]:
    """The codes a `geo_coverage` list covers ("*" stands for every country code)."""
    codes: set[str] = set()
    for label in labels:
        if label in LABELS:
            codes |= LABELS[label]
        elif _COUNTRY.fullmatch(label):
            codes.add(label)
        else:
            raise UnknownCoverageLabel(f"unknown geo_coverage label {label!r}")
    return frozenset(codes)


def covers(labels: Iterable[str], geo: str | None) -> bool:
    """True if an entry with these labels has data for `geo`; None (no place) always fits."""
    if geo is None:
        return True
    codes = covered_codes(labels)
    is_country = _COUNTRY.fullmatch(geo) is not None and geo not in AGGREGATES
    return geo in codes or ("*" in codes and is_country)


def places(labels: Iterable[str]) -> tuple[list[str], list[str], bool]:
    """What a `geo_coverage` list covers, for a page that filters by place.

    Returns the countries named, the groups named (EU, EA, WORLD), and whether every country
    is covered. The labels are expanded here so no reader has to know what "EFTA countries" means.
    """
    codes = covered_codes(labels)
    named = sorted(c for c in codes if c != "*")
    countries = [c for c in named if c not in AGGREGATES]
    groups = [c for c in named if c in AGGREGATES]
    return countries, groups, "*" in codes
