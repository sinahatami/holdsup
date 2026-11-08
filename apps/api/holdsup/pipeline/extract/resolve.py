"""Turn one model claim into a `ClaimSpec`: code fixes what it can tell for sure from the text
(numbers, operators, periods, places) and records a note for each fix."""

import re

from holdsup.pipeline.claim import (
    CHANGE_TYPES,
    LATEST,
    VAGUE_YEARS,
    Assertion,
    AssertionType,
    Basis,
    ClaimSpec,
    Direction,
    Operator,
)
from holdsup.pipeline.extract.dates import SaidOn, normalize_period
from holdsup.pipeline.extract.numbers import is_among, numbers_in, readings, times_written
from holdsup.pipeline.extract.prompt import Lookback, ModelClaim
from holdsup.pipeline.terms import OfficeTerms, find_holders, pick_term
from holdsup.places import is_name, place_code

_QUOTES = str.maketrans("‘’“”", "''\"\"")


def _norm_text(text: str) -> str:
    return " ".join(text.translate(_QUOTES).split()).casefold()


def normalize_geo(code: str | None) -> str | None:
    """The claim code for what the model wrote: a code, a country name, a demonym ("Italian")
    or a short form ("the UK", "America"); None when the place is unknown."""
    return place_code(code)


def _lookback_start(lookback: Lookback, said: SaidOn) -> tuple[str, str | None]:
    """The start period counted back from when it was said, and a note if approximate."""
    note = None
    if said.text is None:
        note = "lookback counted from today: the text does not say when it was said"
    if lookback.unit == "years":
        return str(said.by.year - lookback.amount), note
    if said.text is not None and len(said.text) == 4:
        note = f"lookback in months counted from the end of {said.text}: no month given"
    months = said.by.year * 12 + said.by.month - 1 - lookback.amount
    return f"{months // 12}-{months % 12 + 1:02d}", note


def _check_assertion(assertion: Assertion, text: str, notes: list[str]) -> Assertion:
    """Drop numbers the text does not write; fix what code can tell for sure."""
    numbers = numbers_in(text)
    a = assertion.model_copy()
    for field in ("value", "start_value", "end_value"):
        value = getattr(a, field)
        if value is not None and not is_among(abs(value), numbers):
            setattr(a, field, None)
            notes.append(f"assertion.{field} {value:g} is not in the text; dropped")
    # "From 25.6% to 33.9%" read as a change of 25.6: the value is one of the levels.
    if (
        a.value is not None
        and (a.type in CHANGE_TYPES or a.type == AssertionType.LEVEL)
        and a.start_value is not None
        and a.end_value is not None
        and any(is_among(a.value, [v]) for v in (a.start_value, a.end_value))
        and times_written(a.value, text) == 1
    ):
        notes.append(f"assertion.value {a.value:g} is a start or end level, not a change; dropped")
        a.value = None
    # "Fell from 11.9% to 7.7%" read as a level: both levels are asserted, and the move between
    # them. Check it as a change (direction plus both levels), in points for a percentage.
    if (
        a.type == AssertionType.LEVEL
        and a.value is None
        and a.start_value is not None
        and a.end_value is not None
    ):
        a.type = (
            AssertionType.PERCENTAGE_POINTS
            if a.unit is not None and "%" in a.unit
            else AssertionType.ABSOLUTE
        )
        if a.direction is None and a.start_value != a.end_value:
            a.direction = Direction.UP if a.end_value > a.start_value else Direction.DOWN
        notes.append(f"'from X to Y' levels: checked as a {a.type} change with both levels")
    # "Today it is 43.3%" with the number put in start_value (or "fell to 7%" only in
    # end_value): a level has one number, and it is the asserted value.
    if a.type == AssertionType.LEVEL and a.value is None:
        stated = [f for f in ("start_value", "end_value") if getattr(a, f) is not None]
        if len(stated) == 1:
            a.value = getattr(a, stated[0])
            if stated[0] == "start_value":
                a.start_value = None
            notes.append(f"level {a.value:g} was in assertion.{stated[0]}; used as the value")
    if a.type == AssertionType.RATIO and a.value is not None and a.value > 0:
        implied = (
            Direction.FLAT if a.value == 1 else (Direction.UP if a.value > 1 else Direction.DOWN)
        )
        if a.direction is None:
            a.direction = implied
        elif a.direction != implied:
            notes.append(f"direction {a.direction} contradicts ratio {a.value:g}")
    return a


# "more than 18%": the words right before the asserted number (longest phrases first).
_OPERATORS = [
    ("no more than", Operator.AT_MOST), ("not more than", Operator.AT_MOST),
    ("at most", Operator.AT_MOST), ("up to", Operator.AT_MOST),
    ("no less than", Operator.AT_LEAST), ("no fewer than", Operator.AT_LEAST),
    ("at least", Operator.AT_LEAST),
    ("more than", Operator.MORE_THAN), ("in excess of", Operator.MORE_THAN),
    ("over", Operator.MORE_THAN), ("above", Operator.MORE_THAN),
    ("less than", Operator.LESS_THAN), ("fewer than", Operator.LESS_THAN),
    ("under", Operator.LESS_THAN), ("below", Operator.LESS_THAN),
]  # fmt: skip
_OPERATOR_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p, _ in _OPERATORS) + r")\s+(\d+(?:[.,]\d+)*)",
    re.IGNORECASE,
)
# Phrases that give a window without dates: read as the 5 years before the claim date.
VAGUE_RE = re.compile(
    r"\b(for years|for many years|in recent years|recent years|recently|lately|"
    r"over the years|for some years)\b",
    re.IGNORECASE,
)


def operator_in(quote: str, value: float) -> Operator | None:
    """The bound written right before `value` in the quote ("more than 18%"), if any."""
    ops = dict(_OPERATORS)
    for m in _OPERATOR_RE.finditer(quote):
        if any(is_among(value, values) for values in readings(m[2])):
            return ops[m[1].casefold()]
    return None


def _assumed_window(assertion: Assertion, quote: str, said: SaidOn) -> tuple[str, str] | None:
    """(start, why) for a trend with no dates, or a change that says "for years" or
    "recently": the 5 years before the claim date."""
    vague = VAGUE_RE.search(quote)
    if assertion.type != AssertionType.TREND and not (vague and assertion.type in CHANGE_TYPES):
        return None
    why = f"'{vague[1]}'" if vague else "no window given"
    start = str(said.by.year - VAGUE_YEARS)
    return start, (
        f"{why} read as the {VAGUE_YEARS} years before the claim date ({said.text or 'today'}): "
        f"from {start}"
    )


def resolve(
    claim: ModelClaim,
    *,
    text: str,
    speaker: str | None,
    said: SaidOn,
    terms: OfficeTerms | None = None,
) -> ClaimSpec:
    """Build a `ClaimSpec` from the model's answer. Code decides periods it can compute."""
    notes: list[str] = []

    geo = normalize_geo(claim.geo)
    if claim.geo is not None and geo is None:
        notes.append(f"geo {claim.geo!r} is not a known place; dropped")
    elif claim.geo is not None and is_name(claim.geo):
        notes.append(f"geo {claim.geo!r} read as {geo}")
    geo_basis = None if geo is None else (Basis.STATED if claim.geo_named else Basis.INFERRED)
    peers = []
    for raw in claim.peers:
        if (code := normalize_geo(raw)) is None:
            notes.append(f"peer {raw!r} is not a known place; dropped")
        elif code not in peers:
            peers.append(code)
            if is_name(raw):
                notes.append(f"peer {raw!r} read as {code}")

    start = normalize_period(claim.start)
    if claim.start is not None and start is None:
        notes.append(f"start {claim.start!r} is not a period; dropped")
    start_basis = None if start is None else (Basis.STATED if claim.start_named else Basis.INFERRED)
    end = normalize_period(claim.end, allow_latest=True)
    if claim.end is not None and end is None:
        notes.append(f"end {claim.end!r} is not a period; dropped")
    end_basis = None if end is None else Basis.STATED

    if claim.lookback is not None and claim.lookback.amount > 0:
        computed, note = _lookback_start(claim.lookback, said)
        if start is not None and start != computed:
            notes.append(f"model start {start} replaced by the lookback")
        start, start_basis = computed, Basis.LOOKBACK
        notes.extend([note] if note else [])
        if end is None:
            end, end_basis = (said.text[:7] if said.text else LATEST), Basis.LOOKBACK

    if claim.office is not None:
        holders = find_holders(claim.office.who, geo, terms) or find_holders(
            claim.office.who, None, terms
        )
        if len(holders) != 1:
            found = ", ".join(h.name for h in holders) or "none"
            notes.append(f"office of {claim.office.who!r}: {found} in office_terms.yaml")
        elif (term := pick_term(holders[0], said.by, previous=claim.office.previous)) is None:
            notes.append(f"office of {holders[0].name}: no term matches the date {said.by}")
        else:
            holder = holders[0]
            office_start = f"{term.start:%Y-%m}"
            if start is not None and start != office_start:
                notes.append(f"model start {start} replaced by {holder.name}'s term")
            start, start_basis = office_start, Basis.OFFICE
            if claim.office.scope == "term":
                end = LATEST if term.end is None else f"{term.end:%Y-%m}"
                end_basis = Basis.OFFICE
            if geo is None:
                geo, geo_basis = holder.country, Basis.OFFICE
            elif geo != holder.country:
                notes.append(f"geo {geo} differs from {holder.name}'s country {holder.country}")

    assertion = _check_assertion(claim.assertion, text, notes)
    if (
        assertion.operator is Operator.ABOUT
        and assertion.value is not None
        and (bound := operator_in(claim.quote, assertion.value)) is not None
    ):
        assertion.operator = bound
        notes.append(f"operator {bound} from the text")

    if start is None and (window := _assumed_window(assertion, claim.quote, said)) is not None:
        start, start_basis = window[0], Basis.ASSUMED
        notes.append(window[1])
        if end is None:
            end, end_basis = LATEST, Basis.ASSUMED

    if _norm_text(claim.quote) not in _norm_text(text):
        notes.append("quote is not an exact span of the text")

    return ClaimSpec(
        quote=claim.quote,
        indicator_phrase=claim.indicator_phrase.strip(),
        geo=geo,
        geo_basis=geo_basis,
        peers=peers,
        start=start,
        start_basis=start_basis,
        end=end,
        end_basis=end_basis,
        assertion=assertion,
        speaker=speaker,
        said_on=said.text,
        notes=notes,
    )
