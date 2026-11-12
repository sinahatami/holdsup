"""Distortion checks (P3.4, D026): does the claim's conclusion survive a fairer reading?

Each check that applies to a claim gives one `DistortionCheck`, flagged or not, with one line
saying what it found, in numbers code computed. A flagged check makes a claim that holds
"supported, but framing matters" (docs/spec.md, "Verdicts").

- endpoints: the claim's start or end on a peak, a trough or a turn in the trend (P3.3, D025).
- per_capita: an amount or a count divided by the place's population.
- real: money at current prices adjusted for inflation, with the statistic's real version when
  the catalog has one, otherwise with consumer prices.
- points: a change in a rate that is right in percentage points but stated in percent, or the
  other way round.
- definition: what the claim states (ages, per person, currency, the EU's members) against the
  statistic's definition.
- stale: a claim about the present whose latest figure is two or more years old.

The per-capita and real checks rerun the claim's own operation over its own window and ask the
claim's direction, not its number, like the cherry-pick sweep (D023): divided by population or
adjusted for prices, every claim gets another number, honest or not.
"""

import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from holdsup.catalog.schema import Frequency, IndicatorSpec
from holdsup.checks.changepoints import ChangePoints, checks_endpoints, flag_text
from holdsup.checks.cherry_pick import SWEPT_OPS, own_window, rerun
from holdsup.fmt import fmt, signed, unit_suffix
from holdsup.ops import (
    ChangeKind,
    OpError,
    OpRecord,
    Series,
    chain_index,
    change,
    deflate,
    is_rate,
    months_since,
    parse_period,
    per_capita,
    per_person_unit,
    unit_scale,
)
from holdsup.pipeline.claim import AssertionType, ClaimSpec, Direction, says_now
from holdsup.pipeline.population import wants_population
from holdsup.verdict.rules import assertion_judge, direction_judge
from holdsup.verdict.tolerances import Tolerances


class CheckKind(StrEnum):
    ENDPOINTS = "endpoints"
    PER_CAPITA = "per_capita"
    REAL = "real"
    POINTS = "points"
    DEFINITION = "definition"
    STALE = "stale"


class DistortionCheck(BaseModel):
    """One check that applied to the claim: whether it flags it, and one line saying why."""

    kind: CheckKind
    flagged: bool
    text: str  # a clause, as the verdict's reason uses it: "per person it also fell: ..."
    records: list[OpRecord] = Field(default_factory=list)  # the operations it ran
    uses: str | None = None  # the indicator id of a series it read besides the claim's


@dataclass(frozen=True)
class Related:
    """A series fetched for a check (population, prices, a real version), and its entry."""

    spec: IndicatorSpec
    series: Series


@dataclass(frozen=True)
class CheckInput:
    claim: ClaimSpec
    spec: IndicatorSpec  # the matched statistic
    answer: Sequence[OpRecord]  # the records that decide the claim
    series: Series | None  # the series the first answer read, as it read it
    unit: str | None  # that series' unit
    tolerances: Tolerances
    today: date
    # The first and the last day the claim can have been made ("2019" → 1 January and
    # 31 December 2019); None when it is not dated.
    said: tuple[date, date] | None = None
    adjusted: bool = False  # the answer read a series the plan made (per person, deflated)
    changepoints: ChangePoints | None = None
    population: Related | None = None
    real: Related | None = None  # the statistic at constant prices (`real_version`)
    prices: Related | None = None  # yearly consumer price inflation, in % (to deflate with)


def distortion_checks(inp: CheckInput) -> list[DistortionCheck]:
    """Every check that applies to the claim, in the order the reader sees them."""
    checks: tuple[Callable[[CheckInput], DistortionCheck | None], ...] = (
        endpoints_check,
        per_capita_check,
        real_check,
        points_check,
        definition_check,
        stale_check,
    )
    return [check for run in checks if (check := run(inp)) is not None]


def said_between(said_on: str | None, by: date | None) -> tuple[date, date] | None:
    """The first and last day a claim dated `said_on` ("YYYY", "YYYY-MM" or "YYYY-MM-DD") can
    have been made, `by` being the last (from `parse_said_on`)."""
    if said_on is None or by is None:
        return None
    m = re.fullmatch(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", said_on)
    if m is None:
        return None
    first = date(int(m[1]), int(m[2] or 1), int(m[3] or 1))
    return min(first, by), by


# --- the start and end (P3.3) ----------------------------------------------------------------


def endpoints_check(inp: CheckInput) -> DistortionCheck | None:
    if inp.changepoints is None or len(inp.answer) != 1 or inp.series is None:
        return None
    record = inp.answer[0]
    if not checks_endpoints(inp.claim, record, inp.series):
        return None
    if inp.changepoints.flags:
        text = "; ".join(flag_text(f, record.unit) for f in inp.changepoints.flags)
        return DistortionCheck(kind=CheckKind.ENDPOINTS, flagged=True, text=text)
    start, end = record.inputs[0].period, record.inputs[1].period
    text = (
        f"neither the start ({start}) nor the end ({end}) is at a peak, a trough or a turn in "
        "the trend that carries the claim"
    )
    return DistortionCheck(kind=CheckKind.ENDPOINTS, flagged=False, text=text)


# --- reruns on another series: per person, after inflation ------------------------------------


def reruns(claim: ClaimSpec, answer: Sequence[OpRecord], adjusted: bool) -> bool:
    """Whether the claim's answer can be rerun on another series: one change, growth rate or
    trend, claimed to rise, fall or stay flat, read from a series the plan did not make."""
    return (
        len(answer) == 1
        and not adjusted
        and answer[0].op in SWEPT_OPS
        and claim.assertion.direction is not None
    )


def wants_real_terms(
    claim: ClaimSpec, spec: IndicatorSpec, answer: Sequence[OpRecord], adjusted: bool
) -> bool:
    """Whether the real-terms check applies (so the pipeline fetches what it needs): money at
    current prices, with a real version or yearly (consumer prices are yearly)."""
    if not spec.nominal or not reruns(claim, answer, adjusted):
        return False
    return spec.real_version is not None or spec.frequency is Frequency.ANNUAL


def per_capita_check(inp: CheckInput) -> DistortionCheck | None:
    """Does the claim's direction survive dividing by the place's population?"""
    if not reruns(inp.claim, inp.answer, inp.adjusted) or inp.series is None:
        return None
    if inp.population is None or not wants_population(inp.spec):
        return None
    series, people = inp.series, inp.population.series
    try:
        made = per_capita(
            series,
            people,
            scale=unit_scale(series.unit) / unit_scale(people.unit),
            unit=per_person_unit(series.unit),
        )
        per_person = Series.from_record(made)
        again = rerun(inp.answer[0], per_person, *own_window(inp.answer[0], series))
    except OpError:
        return None
    if again is None:
        return None
    return _direction_check(
        CheckKind.PER_CAPITA, "per person", inp, again, per_person.unit, [made, again],
        uses=inp.population.spec.id,
    )  # fmt: skip


def real_check(inp: CheckInput) -> DistortionCheck | None:
    """Does the claim's direction survive adjusting for inflation? With the statistic's real
    version when the catalog has one; otherwise deflated by consumer prices, in the prices of
    the claim's start."""
    if not wants_real_terms(inp.claim, inp.spec, inp.answer, inp.adjusted) or inp.series is None:
        return None
    record = inp.answer[0]
    try:
        start, end = own_window(record, inp.series)
        if inp.real is not None:
            used, made, real = inp.real, [], inp.real.series
        elif inp.prices is not None:
            used = inp.prices
            index = chain_index(inp.prices.series, str(start))
            deflated = deflate(inp.series, Series.from_record(index), str(start))
            made, real = [index, deflated], Series.from_record(deflated)
        else:
            return None
        again = rerun(record, real, start, end)
    except OpError:
        return None
    if again is None:
        return None
    return _direction_check(
        CheckKind.REAL, "after inflation", inp, again, real.unit, [*made, again],
        uses=used.spec.id,
    )  # fmt: skip


VERB = {Direction.UP: "rose", Direction.DOWN: "fell", Direction.FLAT: "stayed flat"}
TREND_VERB = {Direction.UP: "rises", Direction.DOWN: "falls", Direction.FLAT: "is flat"}


def _direction_check(
    kind: CheckKind,
    how: str,
    inp: CheckInput,
    again: OpRecord,
    unit: str | None,
    records: list[OpRecord],
    *,
    uses: str,
) -> DistortionCheck:
    """Flagged when the rerun does not move the way the claim says (the verdict's own rules,
    without the number); the line says what it did instead. `unit` is the rerun series'."""
    claim, tol = inp.claim, inp.tolerances
    holds = direction_judge(claim, unit=unit, tolerances=tol)(again)
    moved = claim.assertion.direction if holds else _movement(claim, again, unit, tol)
    also = "also " if holds else ""
    if again.op == "trend":
        r2 = again.extras.get("r2")
        fit = f"; R² {r2:.2f}" if r2 is not None else ""
        if moved is None:
            text = f"{how}, there is no clear trend{fit}"
        else:
            slope = f"{signed(again.value or 0.0)}{unit_suffix(again.unit)}"
            text = f"{how}, the trend {also}{TREND_VERB[moved]}: {slope}{fit}"
    else:
        a, b = again.inputs[0], again.inputs[1]
        verb = VERB[moved] if moved is not None else "changed"
        text = (
            f"{how} it {also}{verb}: {fmt(a.value)} in {a.period}, {fmt(b.value)} in "
            f"{b.period}" + (f" ({unit})" if unit else "")
        )
    return DistortionCheck(kind=kind, flagged=not holds, text=text, records=records, uses=uses)


def _movement(
    claim: ClaimSpec, record: OpRecord, unit: str | None, tol: Tolerances
) -> Direction | None:
    """Which way the record moves when not the claimed way: a rise or a fall before "flat";
    None for a trend too weak to have a direction."""
    for d in (Direction.UP, Direction.DOWN, Direction.FLAT):
        if d is claim.assertion.direction:
            continue
        turned = claim.model_copy(
            update={"assertion": claim.assertion.model_copy(update={"direction": d})}
        )
        if direction_judge(turned, unit=unit, tolerances=tol)(record):
            return d
    return None


# --- percent or percentage points -------------------------------------------------------------

OTHER_KIND = {
    ChangeKind.PERCENT: ChangeKind.PERCENTAGE_POINTS,
    ChangeKind.PERCENTAGE_POINTS: ChangeKind.PERCENT,
}
KIND_TEXT = {ChangeKind.PERCENT: "percent", ChangeKind.PERCENTAGE_POINTS: "percentage points"}


def _in(kind: ChangeKind, x: float) -> str:
    return f"{signed(x)}%" if kind is ChangeKind.PERCENT else f"{signed(x)} points"


def points_check(inp: CheckInput) -> DistortionCheck | None:
    """A change in a rate stated in percent or in points: flagged when the claim's number is
    wrong the way it is stated but right the other way (10% to 12% is +2 points but +20%)."""
    a = inp.claim.assertion
    if len(inp.answer) != 1 or a.value is None or inp.series is None or not is_rate(inp.unit):
        return None
    record = inp.answer[0]
    if record.op != "change" or record.value is None:
        return None
    kind = ChangeKind(str(record.args["kind"]))
    if kind not in OTHER_KIND:
        return None
    other = OTHER_KIND[kind]
    try:
        start, end = own_window(record, inp.series)
        again = change(inp.series, str(start), str(end), other, max_distance=0)
    except OpError:
        return None
    read_other = inp.claim.model_copy(
        update={"assertion": a.model_copy(update={"type": AssertionType(str(other))})}
    )
    tol = inp.tolerances
    right = assertion_judge(inp.claim, unit=inp.unit, tolerances=tol)(record)
    right_other = assertion_judge(read_other, unit=inp.unit, tolerances=tol)(again)
    claimed = f"{fmt(a.value)}%" if kind is ChangeKind.PERCENT else f"{fmt(a.value)} points"
    own, theirs = _in(kind, record.value), _in(other, again.value or 0.0)
    if right and right_other:
        text = f"the claimed {claimed} holds both in {KIND_TEXT[kind]} and in {KIND_TEXT[other]}"
    elif right:
        text = (
            f"the claimed {claimed} is right as a change in {KIND_TEXT[kind]} ({own}); "
            f"in {KIND_TEXT[other]} it is {theirs}"
        )
    elif right_other:
        text = (
            f"the claimed {claimed} matches the change in {KIND_TEXT[other]} ({theirs}), "
            f"not in {KIND_TEXT[kind]} ({own})"
        )
    else:
        text = (
            f"read in {KIND_TEXT[other]} instead, the change is {theirs}, which doesn't match "
            f"the claimed {claimed} either"
        )
    flagged = right_other and not right
    return DistortionCheck(kind=CheckKind.POINTS, flagged=flagged, text=text, records=[again])


# --- definition ----------------------------------------------------------------------------

OPEN = math.inf  # an age range with no upper end ("65 and over")
AgeRange = tuple[int | None, float]  # (lowest age or None if not stated, highest age or OPEN)

_N = r"(\d{1,3})"
_WHO = r"(?:age[sd]?|people|persons|those)"
_RANGE = re.compile(
    rf"\b{_WHO}\s+{_N}\s*(?:-|–|to)\s*{_N}\b"
    rf"|\b{_N}\s*(?:-|–|to)\s*{_N}[- ]?years?[- ]?olds?\b",
    re.IGNORECASE,
)
_UNDER = re.compile(
    rf"\b{_WHO}\s+(?:under|below)\s+{_N}\b|\bunder[- ]{_N}s\b|\byounger than\s+{_N}\b"
    rf"|\bunder\s+{_N}[- ]?years?[- ]?olds?\b",
    re.IGNORECASE,
)
_OVER = re.compile(
    rf"\b{_WHO}\s+{_N}\s*(?:\+|and over\b|and older\b|or over\b|or older\b)"
    rf"|\bover[- ]{_N}s\b|\b{_WHO}\s+over\s+{_N}\b|\b(older than)\s+{_N}\b"
    rf"|\b{_N}[- ]?years?[- ]?olds? and (?:over|older)\b",
    re.IGNORECASE,
)


def _numbers(m: re.Match[str]) -> list[int]:
    return [int(g) for g in m.groups() if g is not None and g.isdigit()]


def age_ranges(text: str) -> set[AgeRange]:
    """The age ranges a text states: "aged 15 to 24", "15-24 year olds", "under-25s",
    "aged 65 and over". Numbers without an age word ("2015 to 2024") are not ages."""
    found: set[AgeRange] = set()
    for m in _RANGE.finditer(text):
        lo, hi = _numbers(m)
        if lo <= hi <= 120:
            found.add((lo, float(hi)))
    for m in _UNDER.finditer(text):
        (n,) = _numbers(m)
        if 0 < n <= 120:
            found.add((None, float(n - 1)))
    for m in _OVER.finditer(text):
        (n,) = _numbers(m)
        n += 1 if m.group(0).lower().startswith("older than") else 0  # "older than 64" is 65+
        if n <= 120:
            found.add((n, OPEN))
    return found


def _same_ages(a: AgeRange, b: AgeRange) -> bool:
    """Within a year at each stated end: "over 65" and "aged 65 and over" are one group."""
    lows = a[0] is None or b[0] is None or abs(a[0] - b[0]) <= 1
    highs = a[1] == b[1] or abs(a[1] - b[1]) <= 1
    return lows and highs


def _ages_text(r: AgeRange) -> str:
    lo, hi = r
    if hi == OPEN:
        return f"{lo} and over"
    if lo is None:
        return f"under {int(hi) + 1}"
    return f"{lo} to {int(hi)}"


def _one_range(found: set[AgeRange]) -> AgeRange | None:
    """The one age group a text is about, or None if it names none or several."""
    groups: list[AgeRange] = []
    for r in sorted(found, key=lambda r: (r[0] is None, r[0] or 0, r[1])):
        if not any(_same_ages(r, g) for g in groups):
            groups.append(r)
    return groups[0] if len(groups) == 1 else None


_PER_PERSON = re.compile(
    r"\bper[- ](?:capita|person|head|inhabitant|resident)\b|\ba head\b", re.IGNORECASE
)
_CURRENCIES = {
    "euro": re.compile(r"\beuros?\b|€|\beur\b", re.IGNORECASE),
    "dollars": re.compile(r"\bdollars?\b|\$|\busd\b", re.IGNORECASE),
    "pounds": re.compile(r"\bpounds?\b|£|\bgbp\b|\bsterling\b", re.IGNORECASE),
}
# The EU in every source is today's 27 members; before February 2020 it included the UK.
EU_27_SINCE = date(2020, 2, 1)


def _currency(text: str | None) -> str | None:
    found = [name for name, pattern in _CURRENCIES.items() if text and pattern.search(text)]
    return found[0] if len(found) == 1 else None


def definition_check(inp: CheckInput) -> DistortionCheck | None:
    """What the claim states against the statistic's definition: its age group, per person
    or a total, its currency, and which EU it means. None when the claim states none of them."""
    claim, spec = inp.claim, inp.spec
    stated = f"{claim.indicator_phrase} {claim.assertion.unit or ''}"
    matched: list[str] = []
    differs: list[str] = []

    claimed_ages = _one_range(age_ranges(f"{claim.indicator_phrase} {claim.quote}"))
    covered = _one_range(age_ranges(f"{spec.name} {spec.unit} {spec.definition}"))
    if claimed_ages is not None and covered is not None:
        if _same_ages(claimed_ages, covered):
            matched.append(f"ages {_ages_text(covered)}")
        else:
            differs.append(
                f"the claim is about ages {_ages_text(claimed_ages)}; the statistic covers "
                f"ages {_ages_text(covered)}"
            )

    if _PER_PERSON.search(stated):
        read = inp.unit or spec.unit  # a plan that divided by population reads "per person"
        if _PER_PERSON.search(read):
            matched.append("per person")
        elif wants_population(spec):
            differs.append(f"the claim is per person; the figures are a total ({read})")

    said_in, data_in = _currency(claim.assertion.unit), _currency(spec.unit)
    if said_in is not None and data_in is not None:
        if said_in == data_in:
            matched.append(f"in {data_in}")
        else:
            differs.append(f"the claim is in {said_in}; the statistic is in {data_in}")

    if claim.geo == "EU" and inp.said is not None:
        if inp.said[1] < EU_27_SINCE:
            differs.append(
                f"the claim dates from {claim.said_on}, when the EU included the United "
                "Kingdom; the figures are for the 27 countries in the EU since 2020"
            )
        elif inp.said[0] >= EU_27_SINCE:
            matched.append("the EU's 27 countries")

    if differs:
        return DistortionCheck(kind=CheckKind.DEFINITION, flagged=True, text="; ".join(differs))
    if matched:
        text = f"what the claim states matches the statistic's definition ({', '.join(matched)})"
        return DistortionCheck(kind=CheckKind.DEFINITION, flagged=False, text=text)
    return None


# --- stale data ------------------------------------------------------------------------------


def stale_check(inp: CheckInput) -> DistortionCheck | None:
    """A claim about the present: is its latest figure `stale_years` or more old on the first
    day the claim can have been made (or today, for a claim with no date)?"""
    if not says_now(inp.claim) or not inp.answer or not inp.answer[0].inputs:
        return None
    latest = max((parse_period(p.period) for p in inp.answer[0].inputs), key=lambda p: p.ordinal)
    when = inp.said[0] if inp.said else inp.today
    years = inp.tolerances.distortions.stale_years
    stale = months_since(latest, when) >= 12 * years
    before = f"the claim was made ({inp.claim.said_on})" if inp.said else "today"
    text = (
        f"the latest figure is for {latest}, {years} or more years before {before}"
        if stale
        else f"the latest figure is for {latest}, less than {years} years before {before}"
    )
    return DistortionCheck(kind=CheckKind.STALE, flagged=stale, text=text)
