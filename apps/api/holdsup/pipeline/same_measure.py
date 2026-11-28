"""The same measure from another source, for a claim the matched series has no figures for.

Eurostat's health spending for Italy starts in 2012; the World Bank's, the same measure from
the same health accounts, starts in 2000. A claim about 2005 matches Eurostat's (the match
step reads meaning, not years), then would stop at the calculation for want of a 2005 value.
The fetch step asks these functions first: which of the claim's years the place has no
figures for, and whether an entry the catalog marks `same_measure` has them all.

A year counts as covered when the place has a value within the gap the operations allow
(`max_period_gap`, in years for an annual series; the year itself for a finer one), so the
other source is only used where the matched one could not answer at all.
"""

from collections.abc import Mapping, Sequence

from holdsup.adapters.base import Observation
from holdsup.catalog.schema import IndicatorSpec
from holdsup.ops import LATEST, Frequency
from holdsup.pipeline.claim import ClaimSpec
from holdsup.places import place_name


def claim_years(claim: ClaimSpec) -> list[int]:
    """The years the claim's start and end fall in; "latest" and no date name none."""
    return sorted({int(p[:4]) for p in (claim.start, claim.end) if p and p != LATEST})


def slack_years(spec: IndicatorSpec, max_gap: Mapping[Frequency, int]) -> int:
    """How many years from a claimed year a value may be and still answer it (`max_gap`, the
    tolerances' periods, counts years only for an annual series)."""
    return max_gap.get(Frequency.ANNUAL, 0) if Frequency(spec.frequency) is Frequency.ANNUAL else 0


def missing_years(
    years: Sequence[int], observations: Sequence[Observation], geo: str | None, slack: int
) -> list[int]:
    """The `years` that `geo` has no value within `slack` years of."""
    have = {int(o.period[:4]) for o in observations if o.geo == geo and o.value is not None}
    return [y for y in years if not any(abs(y - h) <= slack for h in have)]


def swap_note(
    matched: IndicatorSpec, used: IndicatorSpec, geo: str | None, years: Sequence[int]
) -> str:
    """What the receipt and the fetch step say when the other source is used. Sources only:
    the statistic's name is on the page already, and many names carry their source."""
    when = ", ".join(str(y) for y in years)
    label = matched.source.label
    return (
        f"{label[:1].upper()}{label[1:]} has no figures for {place_name(geo)} in {when}, so the "
        f"same measure from {used.source.label} was used."
    )
