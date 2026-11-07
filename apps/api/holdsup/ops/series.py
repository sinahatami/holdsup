"""One place's values over time, at one frequency, without gaps written as None."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from holdsup.adapters.base import Observation
from holdsup.ops.periods import Frequency, Period, parse_period
from holdsup.ops.record import DataPoint, OpError, OpRecord


@dataclass(frozen=True)
class Series:
    geo: str
    frequency: Frequency
    points: tuple[tuple[Period, float], ...]  # sorted by period, one value per period
    unit: str | None = None
    _index: dict[Period, float] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.points:
            raise OpError(f"no values for {self.geo}")
        ordinals = [p.ordinal for p, _ in self.points]
        if any(p.frequency is not self.frequency for p, _ in self.points):
            raise OpError(f"{self.geo}: periods of more than one frequency")
        if ordinals != sorted(set(ordinals)):
            raise OpError(f"{self.geo}: periods must be sorted and unique")
        object.__setattr__(self, "_index", dict(self.points))

    @classmethod
    def from_values(
        cls, geo: str, values: Mapping[str, float], unit: str | None = None
    ) -> "Series":
        parsed = [(parse_period(k), float(v)) for k, v in values.items()]
        if not parsed:
            raise OpError(f"no values for {geo}")
        parsed.sort(key=lambda pv: pv[0].ordinal)
        frequency = parsed[0][0].frequency
        return cls(geo, frequency, tuple(parsed), unit)

    @classmethod
    def from_observations(
        cls, observations: Iterable[Observation], geo: str, unit: str | None = None
    ) -> "Series":
        """The `geo` rows of an adapter result; empty cells are skipped.

        Two rows for one period mean the filters selected more than one series: an error, so
        a value is never picked at random.
        """
        values: dict[str, float] = {}
        for o in observations:
            if o.geo != geo or o.value is None:
                continue
            if o.period in values:
                raise OpError(f"{geo}: two values for {o.period}; filters select several series")
            values[o.period] = o.value
        return cls.from_values(geo, values, unit)

    @classmethod
    def from_record(cls, record: OpRecord) -> "Series":
        """The output series of a series op (`per_capita`, `deflate`)."""
        if not record.series:
            raise OpError(f"{record.op} has no output series")
        geo = record.series[0].geo
        return cls.from_values(geo, {p.period: p.value for p in record.series}, record.unit)

    def until(self, last: Period) -> "Series":
        """The values up to and including `last` (same frequency)."""
        if last.frequency is not self.frequency:
            raise OpError(f"{last} is {last.frequency} but the series is {self.frequency}")
        kept = tuple((p, v) for p, v in self.points if p.ordinal <= last.ordinal)
        if not kept:
            raise OpError(f"{self.geo} has no value up to {last}")
        return Series(self.geo, self.frequency, kept, self.unit)

    def get(self, period: Period) -> float | None:
        return self._index.get(period)

    @property
    def first(self) -> Period:
        return self.points[0][0]

    @property
    def last(self) -> Period:
        return self.points[-1][0]

    def point(self, period: Period, value: float) -> DataPoint:
        return DataPoint(geo=self.geo, period=str(period), value=value)

    def data_points(self) -> list[DataPoint]:
        return [self.point(p, v) for p, v in self.points]
