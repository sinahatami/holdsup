"""Period checks shared by validation and repair: which forms a call may write, and order."""

from holdsup.ops import LATEST, Frequency, OpError, parse_period
from holdsup.pipeline.claim import ClaimSpec
from holdsup.pipeline.plan.model import PERIOD_FORMAT, OpName, SeriesInfo
from holdsup.pipeline.plan.operations import OPERATIONS


def yearly_allowed(op: OpName, info: SeriesInfo) -> bool:
    """Whether `op` may take a whole year (YYYY) on this series: a trend reads the year's
    months; other operations need the catalog's rule for a year's value."""
    spec = OPERATIONS[op]
    if info.frequency is Frequency.ANNUAL or spec.reads_months:
        return True
    return info.annual is not None and not spec.makes_series


def period_error(value: str, info: SeriesInfo, op: OpName = "value_at") -> str | None:
    if value == LATEST:
        return None
    try:
        p = parse_period(value)
    except OpError:
        return f"{value!r} is not a period"
    if p.frequency is info.frequency:
        return None
    if p.frequency is Frequency.ANNUAL and yearly_allowed(op, info):
        return None
    if p.frequency is Frequency.ANNUAL:
        return f"{value!r}: {info.id} has no yearly value; use {PERIOD_FORMAT[info.frequency]}"
    form = PERIOD_FORMAT[info.frequency]
    if info.frequency is not Frequency.ANNUAL and yearly_allowed(op, info):
        form = f"YYYY or {form}"
    return f"{value!r} must be {form} for the {info.frequency} {info.id}"


def frequency_of(value: str | None) -> Frequency | None:
    """The frequency a period argument is written in; None for latest or a bad period."""
    if value is None or value == LATEST:
        return None
    try:
        return parse_period(value).frequency
    except OpError:
        return None


def claim_years(claim: ClaimSpec) -> set[str]:
    """Years the claim names as whole years ("in 2015"), and no month or quarter of."""
    periods = [p for p in (claim.start, claim.end) if p and p != LATEST]
    whole = {p for p in periods if len(p) == 4}
    return whole - {p[:4] for p in periods if len(p) > 4}


def period_order(period: str) -> float | None:
    """Where a period falls in time ("latest" last); None if it is not a period."""
    if period == LATEST:
        return float("inf")
    try:
        return float(parse_period(period).ordinal)
    except (ValueError, OpError):
        return None


def is_reversed(start: str | None, end: str | None, info: SeriesInfo, op: OpName) -> bool:
    """Both periods valid and `end` not after `start` ("latest" is always after)."""
    if not start or not end or LATEST in (start, end):
        return False
    if period_error(start, info, op) or period_error(end, info, op):
        return False
    return parse_period(start).ordinal >= parse_period(end).ordinal
