"""JSON-stat 2.0 decoder: dimension ordering, missing values, status flags, malformed input."""

import itertools
import json
import math
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from holdsup.adapters.base import SourceFormatError
from holdsup.adapters.jsonstat import flat_index, label_of, observations, parse_cube

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "eurostat"


def cube(
    *,
    dims: dict[str, object],
    sizes: list[int],
    value: object,
    status: object = None,
    extra: dict[str, object] | None = None,
) -> bytes:
    doc: dict[str, object] = {
        "version": "2.0",
        "class": "dataset",
        "label": "Test",
        "id": list(dims),
        "size": sizes,
        "dimension": {d: {"category": {"index": idx}} for d, idx in dims.items()},
        "value": value,
    }
    if status is not None:
        doc["status"] = status
    doc.update(extra or {})
    return json.dumps(doc).encode()


def by_key(raw: bytes) -> dict[tuple[str, str], float | None]:
    return {(o.geo, o.period): o.value for o in observations(parse_cube(raw))}


# --- ordering ---------------------------------------------------------------------------------


def test_row_major_order_last_dimension_fastest() -> None:
    raw = cube(
        dims={"geo": ["IT", "DE"], "time": ["2020", "2021", "2022"]},
        sizes=[2, 3],
        value=[1, 2, 3, 4, 5, 6],
    )
    assert by_key(raw) == {
        ("IT", "2020"): 1, ("IT", "2021"): 2, ("IT", "2022"): 3,
        ("DE", "2020"): 4, ("DE", "2021"): 5, ("DE", "2022"): 6,
    }  # fmt: skip


def test_object_index_uses_positions_not_key_order() -> None:
    raw = cube(
        # Keys deliberately out of position order.
        dims={"time": {"2022": 2, "2020": 0, "2021": 1}, "geo": {"DE": 1, "IT": 0}},
        sizes=[3, 2],
        value=[1, 2, 3, 4, 5, 6],
    )
    assert by_key(raw) == {
        ("IT", "2020"): 1, ("DE", "2020"): 2,
        ("IT", "2021"): 3, ("DE", "2021"): 4,
        ("IT", "2022"): 5, ("DE", "2022"): 6,
    }  # fmt: skip
    periods = [o.period for o in observations(parse_cube(raw))]
    assert periods == ["2020", "2020", "2021", "2021", "2022", "2022"]


def test_other_dimensions_are_kept_on_each_observation() -> None:
    raw = cube(
        dims={"freq": ["A"], "sex": ["F", "M"], "geo": ["IT"], "time": ["2020"]},
        sizes=[1, 2, 1, 1],
        value=[10, 20],
    )
    obs = observations(parse_cube(raw))
    assert [(o.dims, o.value) for o in obs] == [
        ({"freq": "A", "sex": "F"}, 10.0),
        ({"freq": "A", "sex": "M"}, 20.0),
    ]


@given(st.lists(st.integers(min_value=1, max_value=4), min_size=1, max_size=4))
def test_flat_index_is_a_bijection_onto_the_cube(sizes: list[int]) -> None:
    cells = list(itertools.product(*(range(s) for s in sizes)))
    indices = [flat_index(c, sizes) for c in cells]
    assert indices == list(range(math.prod(sizes)))


# --- missing values ---------------------------------------------------------------------------


def test_sparse_values_leave_missing_cells_as_none() -> None:
    raw = cube(
        dims={"geo": ["IT", "DE"], "time": ["2020", "2021"]},
        sizes=[2, 2],
        value={"0": 1.5, "3": 4.5},
    )
    assert by_key(raw) == {
        ("IT", "2020"): 1.5, ("IT", "2021"): None,
        ("DE", "2020"): None, ("DE", "2021"): 4.5,
    }  # fmt: skip
    present = observations(parse_cube(raw), include_missing=False)
    assert [(o.geo, o.period) for o in present] == [("IT", "2020"), ("DE", "2021")]


def test_dense_values_with_nulls() -> None:
    raw = cube(
        dims={"geo": ["IT"], "time": ["2020", "2021", "2022"]}, sizes=[1, 3], value=[1, None, 3]
    )
    assert by_key(raw) == {("IT", "2020"): 1.0, ("IT", "2021"): None, ("IT", "2022"): 3.0}


def test_empty_cube() -> None:
    raw = cube(dims={"geo": ["IT"], "time": []}, sizes=[1, 0], value={})
    assert observations(parse_cube(raw)) == []


# --- status flags -----------------------------------------------------------------------------


def test_sparse_status_and_status_labels() -> None:
    raw = cube(
        dims={"geo": ["IT"], "time": ["2020", "2021", "2022"]},
        sizes=[1, 3],
        value=[1, 2, None],
        status={"1": "p", "2": "c"},
        extra={"extension": {"status": {"label": {"p": "provisional", "c": "confidential"}}}},
    )
    c = parse_cube(raw)
    assert [(o.period, o.value, o.status) for o in observations(c)] == [
        ("2020", 1.0, None),
        ("2021", 2.0, "p"),
        ("2022", None, "c"),  # flagged but no value
    ]
    assert c.status_labels == {"p": "provisional", "c": "confidential"}


def test_single_string_status_applies_to_every_cell() -> None:
    raw = cube(
        dims={"geo": ["IT"], "time": ["2020", "2021"]}, sizes=[1, 2], value=[1, 2], status="e"
    )
    assert {o.status for o in observations(parse_cube(raw))} == {"e"}


def test_dense_status_array() -> None:
    raw = cube(
        dims={"geo": ["IT"], "time": ["2020", "2021"]},
        sizes=[1, 2],
        value=[1, 2],
        status=[None, "b"],
    )
    assert [o.status for o in observations(parse_cube(raw))] == [None, "b"]


# --- malformed input --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"<html>", "not JSON"),
        (b"[]", "document"),
        (json.dumps({"class": "collection"}).encode(), "class"),
        (json.dumps({"id": ["geo"], "size": "1"}).encode(), "id/size"),
        (json.dumps({"id": ["geo", "time"], "size": [1]}).encode(), "length"),
        (json.dumps({"id": ["geo"], "size": [-1]}).encode(), "bad size"),
        (cube(dims={"geo": ["IT"], "time": ["2020"]}, sizes=[1, 1], value=[1, 2]), "2 entries"),
        (cube(dims={"geo": ["IT"], "time": ["2020"]}, sizes=[1, 1], value={"5": 1}), "outside"),
        (cube(dims={"geo": ["IT"], "time": ["2020"]}, sizes=[1, 1], value={"x": 1}), "non-integer"),
        (cube(dims={"geo": ["IT"], "time": ["2020"]}, sizes=[1, 1], value=["1.0"]), "not a number"),
        (cube(dims={"geo": ["IT"], "time": ["2020"]}, sizes=[1, 1], value="1"), "array or object"),
        (cube(dims={"geo": {"IT": 3}, "time": ["2020"]}, sizes=[1, 1], value=[1]), "bad position"),
        (cube(dims={"geo": ["IT", "DE"], "time": ["2020"]}, sizes=[1, 1], value=[1]), "match size"),
        (cube(dims={"geo": None, "time": ["2020"]}, sizes=[1, 1], value=[1]), "index missing"),
    ],
)
def test_malformed_documents_raise(raw: bytes, message: str) -> None:
    with pytest.raises(SourceFormatError, match=message):
        parse_cube(raw)


def test_missing_geo_or_time_dimension_raises() -> None:
    raw = cube(dims={"country": ["IT"], "time": ["2020"]}, sizes=[1, 1], value=[1])
    with pytest.raises(SourceFormatError, match="'geo'"):
        observations(parse_cube(raw))


def test_non_finite_numbers_become_missing() -> None:
    raw = (
        b'{"class":"dataset","id":["geo","time"],"size":[1,1],"value":[NaN],'
        b'"dimension":{"geo":{"category":{"index":["IT"]}},"time":{"category":{"index":["2020"]}}}}'
    )
    assert by_key(raw) == {("IT", "2020"): None}


# --- recorded Eurostat responses --------------------------------------------------------------


def load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_fixture_monthly_multi_geo_matches_single_geo_query() -> None:
    c = parse_cube(load("une_rt_m_youth_monthly.json"))
    obs = observations(c)
    assert c.dims == ["freq", "s_adj", "age", "unit", "sex", "geo", "time"]
    assert len(obs) == 3 * 22
    assert sum(o.value is not None for o in obs) == 60

    values = {(o.geo, o.period): o.value for o in obs}
    # Ground truth from a separate IT-only query (where the flat index is just the time position).
    assert values[("IT", "2025-01")] == 20.6
    assert values[("IT", "2025-06")] == 20.1
    assert values[("IT", "2026-09")] == 19.9
    # 2026-10 is listed in extension.positions-with-no-data: no geo has a value.
    assert {values[(g, "2026-10")] for g in ("EU27_2020", "IT", "CH")} == {None}
    assert obs[0].dims == {
        "freq": "M",
        "s_adj": "SA",
        "age": "Y_LT25",
        "unit": "PC_ACT",
        "sex": "T",
    }
    assert label_of(c.labels, "geo", "IT") == "Italy"
    assert label_of(c.labels, "geo", "XX") == "XX"


def test_fixture_annual_with_status_flags() -> None:
    obs = observations(parse_cube(load("une_rt_a_annual.json")))
    by = {(o.geo, o.period): o for o in obs}
    assert len(obs) == 3 * 12
    # Ground truth from separate single-geo queries.
    assert (by[("IT", "2014")].value, by[("IT", "2025")].value) == (12.9, 6.1)
    assert (by[("FR", "2014")].value, by[("FR", "2025")].value) == (10.3, 7.7)
    assert by[("IT", "2018")].status == "b"  # break in series
    assert [by[("FR", y)].status for y in ("2020", "2021", "2025")] == [None, "d", "d"]


def test_fixture_with_missing_value() -> None:
    c = parse_cube(load("nama_10_gdp_missing.json"))
    by = {(o.geo, o.period): o for o in observations(c)}
    assert len(by) == 3 * 8
    assert by[("LI", "2025")].value is None
    assert by[("LI", "2018")].value == 5666.3
    assert (by[("LI", "2023")].status, by[("LI", "2024")].status) == ("p", "e")
    assert by[("LI", "2024")].value == 8231.2
