"""JSON-stat 2.0 dataset decoder (https://json-stat.org/full/).

A JSON-stat dataset is a flat array over a cube: `id` lists the dimensions in order and
`size` their lengths; cell (i0, i1, ..., in) sits at the row-major flat index, so the last
dimension varies fastest. `value` and `status` may be arrays (dense) or objects keyed by
the flat index as a string (sparse). A category `index` may be an array of codes or an
object mapping code -> position; positions, not object order, are authoritative.
"""

import itertools
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from holdsup.adapters.base import Observation, SourceFormatError

# JSON values parsed by `json`; narrowed with isinstance checks below.
type JSON = None | bool | int | float | str | list["JSON"] | dict[str, "JSON"]


@dataclass(frozen=True)
class Cube:
    label: str
    dims: list[str]
    sizes: list[int]
    codes: list[list[str]]  # per dimension, category codes ordered by position
    labels: dict[str, dict[str, str]]
    values: dict[int, float | None]
    status: dict[int, str]
    status_labels: dict[str, str]
    updated: str | None


def _obj(value: JSON, where: str) -> dict[str, JSON]:
    if not isinstance(value, dict):
        raise SourceFormatError(f"{where}: expected an object")
    return value


def _ordered_codes(index: JSON, size: int, dim: str) -> list[str]:
    if isinstance(index, list):
        codes = [str(c) for c in index]
    elif isinstance(index, dict):
        codes = [""] * size
        for code, pos in index.items():
            if not isinstance(pos, int) or not 0 <= pos < size:
                raise SourceFormatError(f"dimension {dim}: bad position {pos!r} for {code!r}")
            codes[pos] = code
    else:
        raise SourceFormatError(f"dimension {dim}: category.index missing")
    if len(codes) != size or "" in codes:
        raise SourceFormatError(f"dimension {dim}: index does not match size {size}")
    return codes


def _sparse(raw: JSON, total: int, what: str) -> dict[int, JSON]:
    """Normalize a dense array or sparse object to {flat_index: value}."""
    if raw is None:
        return {}
    if isinstance(raw, list):
        if len(raw) != total:
            raise SourceFormatError(f"{what}: {len(raw)} entries for {total} cells")
        return {i: v for i, v in enumerate(raw) if v is not None}
    if isinstance(raw, dict):
        out: dict[int, JSON] = {}
        for key, v in raw.items():
            try:
                i = int(key)
            except ValueError as exc:
                raise SourceFormatError(f"{what}: non-integer key {key!r}") from exc
            if not 0 <= i < total:
                raise SourceFormatError(f"{what}: index {i} outside cube of {total}")
            out[i] = v
        return out
    raise SourceFormatError(f"{what}: expected array or object")


def _number(v: JSON, i: int) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int | float):
        raise SourceFormatError(f"value at {i}: not a number ({v!r})")
    f = float(v)
    return f if math.isfinite(f) else None


def parse_cube(raw: bytes | str) -> Cube:
    try:
        doc = _obj(cast(JSON, json.loads(raw)), "document")
    except json.JSONDecodeError as exc:
        raise SourceFormatError(f"not JSON: {exc}") from exc
    if doc.get("class", "dataset") != "dataset":
        raise SourceFormatError(f"expected class 'dataset', got {doc.get('class')!r}")

    dims_raw, sizes_raw = doc.get("id"), doc.get("size")
    if not isinstance(dims_raw, list) or not isinstance(sizes_raw, list):
        raise SourceFormatError("missing id/size")
    if len(dims_raw) != len(sizes_raw):
        raise SourceFormatError("id and size differ in length")
    dims = [str(d) for d in dims_raw]
    sizes: list[int] = []
    for s in sizes_raw:
        if isinstance(s, bool) or not isinstance(s, int) or s < 0:
            raise SourceFormatError(f"bad size {s!r}")
        sizes.append(s)

    dimension = _obj(doc.get("dimension"), "dimension")
    codes: list[list[str]] = []
    labels: dict[str, dict[str, str]] = {}
    for dim, size in zip(dims, sizes, strict=True):
        category = _obj(_obj(dimension.get(dim), f"dimension {dim}").get("category"), dim)
        codes.append(_ordered_codes(category.get("index"), size, dim))
        raw_labels = category.get("label")
        labels[dim] = (
            {str(k): str(v) for k, v in raw_labels.items()} if isinstance(raw_labels, dict) else {}
        )

    total = math.prod(sizes)
    values = {i: _number(v, i) for i, v in _sparse(doc.get("value"), total, "value").items()}

    status: dict[int, str] = {}
    raw_status = doc.get("status")
    if isinstance(raw_status, str):  # one flag for every cell
        status = dict.fromkeys(range(total), raw_status)
    else:
        status = {i: str(v) for i, v in _sparse(raw_status, total, "status").items()}

    extension = doc.get("extension")
    status_labels: dict[str, str] = {}
    if isinstance(extension, dict) and isinstance(extension.get("status"), dict):
        ext_status = cast(dict[str, JSON], extension["status"])
        if isinstance(ext_status.get("label"), dict):
            status_labels = {
                str(k): str(v) for k, v in cast(dict[str, JSON], ext_status["label"]).items()
            }

    label = doc.get("label")
    updated = doc.get("updated")
    return Cube(
        label=str(label) if label is not None else "",
        dims=dims,
        sizes=sizes,
        codes=codes,
        labels=labels,
        values=values,
        status=status,
        status_labels=status_labels,
        updated=str(updated) if updated is not None else None,
    )


def flat_index(position: Sequence[int], sizes: Sequence[int]) -> int:
    """Row-major flat index of a cell (last dimension varies fastest)."""
    index = 0
    for pos, size in zip(position, sizes, strict=True):
        index = index * size + pos
    return index


def observations(
    cube: Cube, *, geo_dim: str = "geo", time_dim: str = "time", include_missing: bool = True
) -> list[Observation]:
    """One Observation per cell, in cube order. Missing cells have value None."""
    for required in (geo_dim, time_dim):
        if required not in cube.dims:
            raise SourceFormatError(f"dataset has no {required!r} dimension")
    others = [d for d in cube.dims if d not in (geo_dim, time_dim)]
    out: list[Observation] = []
    for position in itertools.product(*(range(s) for s in cube.sizes)):
        cell = {
            d: cube.codes[k][p] for k, (d, p) in enumerate(zip(cube.dims, position, strict=True))
        }
        i = flat_index(position, cube.sizes)
        value = cube.values.get(i)
        if value is None and not include_missing:
            continue
        out.append(
            Observation(
                geo=cell[geo_dim],
                period=cell[time_dim],
                value=value,
                status=cube.status.get(i),
                dims={d: cell[d] for d in others},
            )
        )
    return out


def label_of(labels: Mapping[str, Mapping[str, str]], dim: str, code: str) -> str:
    return labels.get(dim, {}).get(code, code)
