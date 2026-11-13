"""The confidence model (P4.5): how likely a claim's verdict is to be right, and when to say
"can't check confidently" instead.

The signals are facts the check already has: how well the reranker thought the statistic fits
the claim, whether the claim's wording differs from the statistic's definition, how old and
how long the series is, how close the computed figure sits to the tolerance's edge, and whether
backup models did the work. A logistic regression trained in ml/confidence/ on the dev split's
evaluation runs turns them into a probability. It is served from `confidence_model.json`:
the imputation means, the scaler, the coefficients and the cut-offs, read by plain Python
(no scikit-learn, no pickle; D032).

Only a claim with a verdict other than cant_check gets a confidence: there is nothing to
abstain from otherwise. Abstaining keeps the verdict the rules gave (the receipt still shows
why); the result says it is not confident, and why, in words code writes from the signals.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from holdsup.ops import OpError, months_since, parse_period
from holdsup.pipeline.claim import Operator
from holdsup.verdict.model import Part

MODEL_FILE = Path(__file__).with_name("confidence_model.json")
# A part whose computed figure is this many tolerances or more from the edge counts as far.
MAX_BOUNDARY_DISTANCE = 5.0
MAX_REASONS = 2

ConfidenceLabel = Literal["high", "medium", "low"]


class Signals(BaseModel):
    """What the confidence model reads, as the check found it. None: not known for this claim
    (the model then reads the training mean, which moves nothing)."""

    # The reranker's probability that the matched statistic fits the claim's sentence; None
    # when the reranker did not run (a reader's re-check, or no reranker loaded).
    rerank_probability: float | None = None
    # That probability minus the best other candidate's (negative: the model picked a lower one).
    rerank_margin: float | None = None
    # The definition check flagged a difference (ages, per person, currency, area).
    definition_mismatch: bool = False
    # Years from the newest figure the check read to the day the claim is checked as of.
    data_age_years: float | None = None
    # Values in the series the check read.
    series_length: int | None = None
    # How far the computed figure is from the edge of the tolerance, in tolerances (capped).
    boundary_distance: float | None = None
    # Of extraction, matching and planning: how many a backup model did, not the first choice.
    fallback_steps: int = 0


# The model's inputs in order, with the direction that should mean "more likely right".
# A learned coefficient of the other sign is reported by the trainer and never gives a reason.
FEATURES: tuple[str, ...] = (
    "rerank_probability",
    "rerank_margin",
    "definition_mismatch",
    "data_age_years",
    "series_length",
    "boundary_distance",
    "fallback_steps",
)
EXPECTED_SIGN: Mapping[str, int] = {
    "rerank_probability": 1,
    "rerank_margin": 1,
    "definition_mismatch": -1,
    "data_age_years": -1,
    "series_length": 1,
    "boundary_distance": 1,
    "fallback_steps": -1,
}


def vector(s: Signals) -> list[float | None]:
    """The signals as the model reads them, in `FEATURES` order. The series length is on a log
    scale (ten values against twenty matters, two hundred against two hundred and ten does not)."""
    return [
        s.rerank_probability,
        s.rerank_margin,
        1.0 if s.definition_mismatch else 0.0,
        None if s.data_age_years is None else max(0.0, s.data_age_years),
        None if s.series_length is None else math.log1p(s.series_length),
        s.boundary_distance,
        float(s.fallback_steps),
    ]


# --- the signals -----------------------------------------------------------------------------


def rerank_signals(
    candidates: Sequence[tuple[str, float | None]], matched: str
) -> tuple[float | None, float | None]:
    """The matched statistic's reranker probability and its margin over the best other
    candidate (over 0 when it was the only one). (None, None) when the reranker did not score
    the matched statistic."""
    scores = dict(candidates)
    mine = scores.get(matched)
    if mine is None:
        return None, None
    others = [p for i, p in candidates if i != matched and p is not None]
    return round(mine, 4), round(mine - max(others, default=0.0), 4)


def data_age_years(last_period: str | None, as_of: date) -> float | None:
    """Years from the end of `last_period` to `as_of`; None for no period or one that cannot
    be read."""
    if last_period is None:
        return None
    try:
        return round(months_since(parse_period(last_period), as_of) / 12, 2)
    except OpError:
        return None


def boundary_distance(parts: Sequence[Part]) -> float | None:
    """The closest call among the verdict's parts: how many tolerances the computed figure is
    from where the part would flip between holding and not. None when no part has a tolerance
    (a direction-only claim)."""
    distances = [d for p in parts if (d := _part_distance(p)) is not None]
    return round(min(distances), 4) if distances else None


def _part_distance(p: Part) -> float | None:
    if p.computed is None or p.asserted is None or p.tolerance is None or p.tolerance <= 0:
        return None
    band = p.tolerance
    if p.operator is Operator.ABOUT:
        gap = abs(abs(p.computed - p.asserted) - band)
    else:
        # Bounds compare sizes in the claimed direction, as the verdict rules do.
        c, t = (-p.computed, -p.asserted) if p.asserted < 0 else (p.computed, p.asserted)
        edge = {
            Operator.MORE_THAN: t,
            Operator.LESS_THAN: t,
            Operator.AT_LEAST: t - band,
            Operator.AT_MOST: t + band,
        }[p.operator]
        gap = abs(c - edge)
    return min(gap / band, MAX_BOUNDARY_DISTANCE)


# --- the model -------------------------------------------------------------------------------


class TrainedOn(BaseModel):
    """Where a model came from: enough to rebuild it (ml/confidence/reports/report.json has
    the rest)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    created: str  # the day it was trained, ISO
    eval_version: str
    catalog_version: str
    reports: dict[str, str]  # the dev evaluation reports read -> sha256
    rows: int
    seed: int
    # Cross-validated on the dev split: Brier score, the base rate's, coverage at the threshold...
    metrics: dict[str, float] = Field(default_factory=dict)


class ConfidenceModel(BaseModel):
    """A logistic regression on the standardized signals, and its cut-offs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    features: list[str]
    impute: list[float]  # the training mean of each feature: what a missing signal reads as
    center: list[float]  # the scaler's mean
    scale: list[float]  # the scaler's standard deviation (1 for a constant feature)
    coef: list[float]
    intercept: float
    # Below `threshold` the check abstains; at `high` or above the confidence is high.
    threshold: float = Field(ge=0, le=1)
    high: float = Field(ge=0, le=1)
    target_accuracy: float = Field(gt=0, le=1)  # what the threshold was chosen to keep
    trained_on: TrainedOn

    @model_validator(mode="after")
    def _consistent(self) -> "ConfidenceModel":
        if tuple(self.features) != FEATURES:
            raise ValueError(f"the model's features {self.features} are not {list(FEATURES)}")
        n = len(FEATURES)
        for name in ("impute", "center", "scale", "coef"):
            if len(getattr(self, name)) != n:
                raise ValueError(f"{name} needs {n} values")
        if any(s <= 0 for s in self.scale):
            raise ValueError("every scale must be positive")
        if self.high < self.threshold:
            raise ValueError("the high cut-off cannot be below the abstention threshold")
        return self

    @property
    def name(self) -> str:
        """How receipts name it."""
        return f"logistic regression (trained {self.trained_on.created})"

    def standardized(self, s: Signals) -> list[float]:
        raw = vector(s)
        filled = [m if x is None else x for x, m in zip(raw, self.impute, strict=True)]
        return [(x - c) / sc for x, c, sc in zip(filled, self.center, self.scale, strict=True)]

    def contributions(self, s: Signals) -> list[float]:
        """Each feature's push on the log-odds, against an average claim."""
        return [w * z for w, z in zip(self.coef, self.standardized(s), strict=True)]

    def probability(self, s: Signals) -> float:
        logit = self.intercept + sum(self.contributions(s))
        return 1 / (1 + math.exp(-logit))

    def score(self, s: Signals) -> "Confidence":
        p = self.probability(s)
        abstain = p < self.threshold
        label: ConfidenceLabel = "low" if abstain else "high" if p >= self.high else "medium"
        return Confidence(
            signals=s,
            probability=round(p, 4),
            label=label,
            abstain=abstain,
            reason=self.reason(s) if abstain else None,
            model=self.name,
        )

    def reason(self, s: Signals) -> str:
        """Why a claim scored low, from the signals that pulled it down most. A signal counts
        only when it is on its worse side and its learned weight points the expected way."""
        raw = vector(s)
        pulls = []
        for i, (name, push) in enumerate(zip(FEATURES, self.contributions(s), strict=True)):
            sign = EXPECTED_SIGN[name]
            x = raw[i]
            if x is None or push >= 0 or self.coef[i] * sign <= 0:
                continue
            if (x - self.center[i]) * sign >= 0:
                continue
            pulls.append((push, name))
        why = [_REASONS[name](s) for _, name in sorted(pulls)[:MAX_REASONS]]
        if not why:
            return f"{NOT_CONFIDENT} {GENERIC_REASON}"
        return f"{NOT_CONFIDENT} {_join(why)}."


class Confidence(BaseModel):
    """How sure the check is of a claim's verdict."""

    signals: Signals
    probability: float | None = None  # the verdict's chance of being right; None: no model
    label: ConfidenceLabel | None = None
    abstain: bool = False  # too unsure to give the verdict as the answer
    reason: str | None = None  # why it abstains, in plain words
    model: str | None = None


NOT_CONFIDENT = "HoldsUp is not confident in this verdict:"
GENERIC_REASON = "claims like this one were often answered wrongly in its benchmark."


def _years(n: float) -> str:
    whole = round(n)
    return "less than a year" if whole < 1 else f"about {whole} year{'s' if whole != 1 else ''}"


_REASONS: Mapping[str, Callable[[Signals], str]] = {
    "rerank_probability": lambda s: (
        "the statistic it matched is not a clear fit for the claim's wording"
    ),
    "rerank_margin": lambda s: (
        "another statistic fits the claim's wording almost as well as the one used"
    ),
    "definition_mismatch": lambda s: (
        "what the claim describes differs from the statistic's definition"
    ),
    "data_age_years": lambda s: (
        f"the newest figure it could use is {_years(s.data_age_years or 0)} old"
    ),
    "series_length": lambda s: f"the series has only {s.series_length} values",
    "boundary_distance": lambda s: (
        "the computed figure is close to the edge of the tolerance, so a small revision of "
        "the data could change the verdict"
    ),
    "fallback_steps": lambda s: "a backup model did part of the work",
}


def _join(parts: Sequence[str]) -> str:
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])}, and {parts[-1]}"


def unscored(s: Signals) -> Confidence:
    """The signals alone, when no model is loaded (the evaluation still records them)."""
    return Confidence(signals=s)


def load_confidence(path: Path = MODEL_FILE) -> ConfidenceModel | None:
    """The trained model, or None before one is trained (`make confidence-train`)."""
    if not path.exists():
        return None
    return ConfidenceModel.model_validate_json(path.read_text(encoding="utf-8"))
