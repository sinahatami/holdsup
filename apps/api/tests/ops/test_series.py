import pytest

from holdsup.adapters.base import Observation
from holdsup.ops import DataPoint, Frequency, OpError, OpRecord, Series, parse_period


def test_from_values_sorts_and_infers_the_frequency() -> None:
    s = Series.from_values("IT", {"2020-Q2": 2.0, "2020-Q1": 1.0}, unit="%")
    assert s.frequency is Frequency.QUARTERLY
    assert [str(p) for p, _ in s.points] == ["2020-Q1", "2020-Q2"]
    assert (str(s.first), str(s.last), s.unit) == ("2020-Q1", "2020-Q2", "%")
    assert s.get(parse_period("2020-Q2")) == 2.0
    assert s.get(parse_period("2020-Q3")) is None


def test_from_observations_keeps_one_geo_and_skips_empty_cells() -> None:
    rows = [
        Observation("IT", "2021", 2.0),
        Observation("IT", "2020", 1.0),
        Observation("IT", "2022", None),
        Observation("DE", "2020", 9.0),
    ]
    s = Series.from_observations(rows, "IT")
    assert s.data_points() == [
        DataPoint(geo="IT", period="2020", value=1.0),
        DataPoint(geo="IT", period="2021", value=2.0),
    ]


def test_two_values_for_one_period_is_an_error() -> None:
    rows = [
        Observation("IT", "2020", 1.0, dims={"sex": "M"}),
        Observation("IT", "2020", 2.0, dims={"sex": "F"}),
    ]
    with pytest.raises(OpError, match="several series"):
        Series.from_observations(rows, "IT")


def test_no_values_is_an_error() -> None:
    with pytest.raises(OpError, match="no values for IT"):
        Series.from_observations([Observation("IT", "2020", None)], "IT")
    with pytest.raises(OpError, match="no values for FR"):
        Series("FR", Frequency.ANNUAL, ())


def test_mixed_frequencies_are_an_error() -> None:
    with pytest.raises(OpError, match="more than one frequency"):
        Series.from_values("IT", {"2020": 1.0, "2020-Q1": 1.0})


def test_points_must_be_sorted_and_unique() -> None:
    a, b = parse_period("2020"), parse_period("2021")
    with pytest.raises(OpError, match="sorted and unique"):
        Series("IT", Frequency.ANNUAL, ((b, 1.0), (a, 2.0)))
    with pytest.raises(OpError, match="sorted and unique"):
        Series("IT", Frequency.ANNUAL, ((a, 1.0), (a, 2.0)))


def test_from_record() -> None:
    record = OpRecord(
        op="per_capita",
        args={},
        inputs=[],
        series=[DataPoint(geo="IT", period="2020", value=3.0)],
        unit="EUR per person",
    )
    s = Series.from_record(record)
    assert (s.geo, s.unit, s.points[0][1]) == ("IT", "EUR per person", 3.0)
    with pytest.raises(OpError, match="no output series"):
        Series.from_record(OpRecord(op="value_at", args={}, inputs=[], value=1.0))
