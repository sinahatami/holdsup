"""Scale words in units ("billion euros", "thousand persons") as multipliers."""

import re

_SCALES = {
    "thousand": 1e3,
    "thousands": 1e3,
    "million": 1e6,
    "millions": 1e6,
    "mio": 1e6,
    "billion": 1e9,
    "billions": 1e9,
    "bn": 1e9,
    "trillion": 1e12,
    "trillions": 1e12,
}


def unit_scale(unit: str | None) -> float:
    """The multiplier a unit's scale word stands for: "million euro" → 1e6, "euro" → 1."""
    if not unit:
        return 1.0
    for word in re.findall(r"[a-z]+", unit.lower()):
        if word in _SCALES:
            return _SCALES[word]
    return 1.0


def is_rate(unit: str | None) -> bool:
    """A unit in percent: rates and shares, compared in points rather than relatively."""
    return unit is not None and unit.strip().startswith("%")


def per_person_unit(unit: str | None) -> str | None:
    """The unit of a series divided by population: "million euro" → "euro per person"."""
    if not unit:
        return None
    bare = re.sub(
        r"\b(thousand|million|billion|trillion|mio|bn)s?\b\s*", "", unit, flags=re.IGNORECASE
    )
    return f"{bare.strip()} per person"
