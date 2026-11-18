"""Numerals as a text writes them, and how precisely: "58.0 million" is written to a tenth of a
million, "58" to the unit. The explanation check reads every numeral it finds (explain.py), and
the verdict reads the precision a claim was stated to (verdict/rules.py): a value that came out
of the model as the float 58.0 no longer says whether the text had a decimal.
"""

import re
from dataclasses import dataclass

from holdsup.ops import unit_scale

_SCALE_WORDS = r"thousand|million|billion|trillion"
# A numeral, optionally followed by a scale word: "1,660,000", "28.1", "-12", "1.7 trillion".
_NUMERAL = re.compile(
    rf"(?<![\w.])-?(\d{{1,3}}(?:,\d{{3}})+|\d+)(\.\d+)?(?:\s*({_SCALE_WORDS})s?\b)?",
    re.IGNORECASE,
)
# Period labels written as dates, not quantities: "2024-Q1", "Q1 2024", "2024-S1", "2024-03".
_PERIODS = re.compile(
    r"\b\d{4}-(?:Q[1-4]|S[12])\b|\b(?:Q[1-4]|S[12])\b|\b\d{4}-(?:0[1-9]|1[0-2])\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Written:
    """One numeral in a text, with how precisely it is written."""

    text: str
    value: float  # with the scale word applied ("1.7 trillion" → 1.7e12)
    half_unit: float  # with the scale word applied


def written_numbers(text: str) -> list[Written]:
    out = []
    for m in _NUMERAL.finditer(_PERIODS.sub(" ", text)):
        grouped, frac, word = m.group(1), m.group(2) or "", m.group(3)
        whole = grouped.replace(",", "")
        number = float(whole + frac)
        if frac:
            half = 0.5 * 10.0 ** -(len(frac) - 1)
        elif "," in grouped and (zeros := len(whole) - len(whole.rstrip("0"))):
            half = 0.5 * 10.0**zeros  # "28,000" is a rounded figure; "2020" is a year
        else:
            half = 0.5
        scale = unit_scale(word)
        out.append(Written(m.group(0).strip(), number * scale, half * scale))
    return out


def written_half_unit(text: str, stated: float, scale: float = 1.0) -> float | None:
    """Half a unit of the last digit of `stated` as `text` writes it, in units of `scale` ("58.0
    million" with a scale of a million → 0.05; "58" → 0.5). None when no numeral in the text is
    that number, so the caller falls back to the float's own digits."""
    for found in written_numbers(text):
        if abs(found.value / scale - abs(stated)) <= 1e-9 * max(1.0, abs(stated)):
            return found.half_unit / scale
    return None
