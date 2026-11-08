"""Second looks: when the model's first answer is worth one more turn, and what to tell it.

Each rule reads the first answer and returns a `Nudge`, or None. The first rule in
`SECOND_LOOKS` that fires is the one asked, so a new reason to ask again is one more rule.
"""

from collections.abc import Callable
from dataclasses import dataclass

from holdsup.catalog.schema import Frequency
from holdsup.pipeline.claim import says_now
from holdsup.pipeline.match.model import MatchAnswer, MatchRun
from holdsup.pipeline.match.prompt import yearly_note


@dataclass(frozen=True)
class Nudge:
    note: str  # recorded in the match's notes
    prompt: str  # what the model is told


SecondLook = Callable[[MatchRun, MatchAnswer | None], Nudge | None]


def yearly_series_turned_down(run: MatchRun, answer: MatchAnswer | None) -> Nudge | None:
    """A monthly or quarterly series with yearly values that the model named but turned down
    (no pick, or a low-confidence one)."""
    if answer is None or (answer.indicator_id is not None and answer.confidence != "low"):
        return None
    named = [answer.indicator_id] if answer.indicator_id else []
    for indicator_id in [*named, *answer.alternatives]:
        spec = run.eligible.get(indicator_id)
        if spec is not None and spec.frequency is not Frequency.ANNUAL and spec.annual_value:
            return Nudge(
                f"asked again: {spec.id} was turned down, and frequency is no reason",
                f"Frequency is not a reason to turn down {spec.id}: it is {spec.frequency}, and "
                f"code makes a year's value from it.{yearly_note(spec)} If it measures the same "
                "thing as the claim (population, unit, definition), pick it; otherwise answer "
                "null again. Answer with the JSON object only.",
            )
    return None


_FINENESS = {
    Frequency.MONTHLY: 0,
    Frequency.QUARTERLY: 1,
    Frequency.SEMIANNUAL: 2,
    Frequency.ANNUAL: 3,
}


def finer_series_for_now(run: MatchRun, answer: MatchAnswer | None) -> Nudge | None:
    """For a claim about the present: the picked series' more frequent alternative (same unit),
    the finest one the model listed. A series with a more frequent twin is out later."""
    if answer is None or answer.indicator_id is None or not says_now(run.claim):
        return None
    picked = run.eligible.get(answer.indicator_id)
    if picked is None:
        return None
    finer = [
        spec
        for i in answer.alternatives
        if (spec := run.eligible.get(i)) is not None
        and spec.unit == picked.unit
        and _FINENESS[spec.frequency] < _FINENESS[picked.frequency]
    ]
    spec = min(finer, key=lambda spec: _FINENESS[spec.frequency], default=None)
    if spec is None:
        return None
    return Nudge(
        f"asked again: {spec.id} is {spec.frequency}, more often than {answer.indicator_id}"
        ", and the claim is about the present",
        f"The claim is about the present, and {spec.id} ({spec.frequency}) is out sooner "
        f"than {answer.indicator_id}. If it measures the same thing as the claim "
        f"(population, unit, definition), pick it;{yearly_note(spec)} otherwise keep "
        f"{answer.indicator_id}. Answer with the JSON object only.",
    )


SECOND_LOOKS: tuple[SecondLook, ...] = (yearly_series_turned_down, finer_series_for_now)


def second_look(run: MatchRun, answer: MatchAnswer | None) -> Nudge | None:
    """The nudge of the first rule that fires, if any."""
    return next((n for look in SECOND_LOOKS if (n := look(run, answer)) is not None), None)
