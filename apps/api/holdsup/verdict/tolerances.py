"""The tolerances verdicts allow: how far a computed value may be from a claimed one.

Loaded from `tolerances.yaml`; its `version` is stored with every verdict, so a stored result
is reused only while the tolerances it came from are current.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from holdsup.ops import Frequency

TOLERANCES = Path(__file__).with_name("tolerances.yaml")


class ValueTolerance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative: float = Field(default=0.0, ge=0)
    absolute: float = Field(default=0.0, ge=0)
    rounding: bool
    # Added on top of the rest, as a share of the asserted value: room for data revisions.
    plus_relative: float = Field(default=0.0, ge=0)

    def band(self, asserted: float) -> float:
        """The largest |computed - asserted| that still holds."""
        rounding = half_unit(asserted) if self.rounding else 0.0
        base = max(self.relative * abs(asserted), self.absolute, rounding)
        return base + self.plus_relative * abs(asserted)


class ValueTolerances(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: ValueTolerance
    level_rate: ValueTolerance
    absolute: ValueTolerance
    percent: ValueTolerance
    percentage_points: ValueTolerance
    ratio: ValueTolerance
    rank: ValueTolerance


class SweepTolerances(BaseModel):
    """Which time windows the cherry-pick sweep counts (D023)."""

    model_config = ConfigDict(extra="forbid")

    reach: int = Field(ge=1)  # years a nearby window's start or end may move
    min_years: float = Field(ge=0)  # the shortest claim window that gets a share


class ChangePointTolerances(BaseModel):
    """When a start or end on a break or extreme carries the claim (D025)."""

    model_config = ConfigDict(extra="forbid")

    shrink: float = Field(gt=0, le=1)  # the share the change may lose before it is flagged


class DistortionTolerances(BaseModel):
    """When a distortion check flags a claim (D026)."""

    model_config = ConfigDict(extra="forbid")

    stale_years: int = Field(ge=1)  # a "now" claim's latest figure at least this old is stale


class Tolerances(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    framing_threshold: float = Field(ge=0, le=1)
    sweep: SweepTolerances
    changepoints: ChangePointTolerances
    distortions: DistortionTolerances
    values: ValueTolerances
    flat_relative: float = Field(ge=0)
    trend_min_r2: float = Field(ge=0, le=1)
    max_period_gap: dict[Frequency, int]


def load_tolerances(path: Path = TOLERANCES) -> Tolerances:
    return Tolerances.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def half_unit(value: float) -> float:
    """Half a unit of the last written digit: 23 → 0.5, 2.3 → 0.05, 0.25 → 0.005."""
    if value.is_integer():
        return 0.5
    text = repr(abs(value))
    if "e" in text:
        return 0.0
    return 0.5 * 10.0 ** -len(text.split(".")[1])
