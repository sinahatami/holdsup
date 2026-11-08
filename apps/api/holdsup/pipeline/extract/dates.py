"""Read periods and "when it was said" dates as the model or the text writes them."""

import calendar
import re
from dataclasses import dataclass
from datetime import date

from holdsup.pipeline.claim import LATEST, PERIOD_RE

MONTHS = {
    name: i
    for i, name in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        1,
    )
}
# "Renzi, 2018: ..." / "Facebook post, May 2013: ..." at the very start of the text.
_ATTRIBUTION = re.compile(r"^\s*[^:\n]{1,80}?,\s*(?:([A-Za-z]+)\s+)?(\d{4})\s*:")


def attribution_date(text: str) -> str | None:
    """The date in a leading attribution ("Facebook post, May 2013:" -> "2013-05")."""
    m = _ATTRIBUTION.match(text)
    if m is None:
        return None
    if m[1] is None:
        return m[2]
    month = MONTHS.get(m[1].casefold())
    return f"{m[2]}-{month:02d}" if month else None


def normalize_period(period: str | None, *, allow_latest: bool = False) -> str | None:
    if period is None:
        return None
    p = period.strip()
    if allow_latest and p.casefold() in {"latest", "now", "today", "current", "present"}:
        return LATEST
    p = p.upper()
    if PERIOD_RE.fullmatch(p):
        return p
    if m := re.fullmatch(r"(\d{4})\s*-?\s*Q([1-4])", p) or re.fullmatch(r"Q([1-4])\s*(\d{4})", p):
        year, quarter = (m[1], m[2]) if len(m[1]) == 4 else (m[2], m[1])
        return f"{year}-Q{quarter}"
    # Half-years: "2024-S1", "2024 H2", "S1 2024" (S1 = January to June, S2 = July to December).
    if m := re.fullmatch(r"(\d{4})\s*-?\s*[SH]([12])", p) or re.fullmatch(
        r"[SH]([12])\s*(\d{4})", p
    ):
        year, half = (m[1], m[2]) if len(m[1]) == 4 else (m[2], m[1])
        return f"{year}-S{half}"
    if m := re.fullmatch(r"(\d{4})-(\d{1,2})(?:-\d{1,2})?", p):
        month = int(m[2])
        return f"{m[1]}-{month:02d}" if 1 <= month <= 12 else None
    return None


@dataclass(frozen=True)
class SaidOn:
    text: str | None  # as normalized: "YYYY", "YYYY-MM", "YYYY-MM-DD"; None if unknown
    by: date  # latest day it can have been said (today when unknown)


def parse_said_on(said_on: str | None, today: date) -> SaidOn:
    if said_on:
        s = said_on.strip()
        try:
            if m := re.fullmatch(r"(\d{4})", s):
                return SaidOn(s, min(date(int(m[1]), 12, 31), today))
            if m := re.fullmatch(r"(\d{4})-(\d{1,2})", s):
                y, mo = int(m[1]), int(m[2])
                bound = date(y, mo, calendar.monthrange(y, mo)[1])
                return SaidOn(f"{y}-{mo:02d}", min(bound, today))
            if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s):
                d = date(int(m[1]), int(m[2]), int(m[3]))
                return SaidOn(d.isoformat(), min(d, today))
        except ValueError:
            pass
    return SaidOn(None, today)
