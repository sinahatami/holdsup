"""Coverage labels: which places a catalog entry has data for."""

import pytest

from holdsup.catalog.coverage import UnknownCoverageLabel, covered_codes, covers
from holdsup.catalog.schema import load_catalog
from holdsup.config import get_settings


@pytest.mark.parametrize(
    ("labels", "geo", "expected"),
    [(["All countries", "WLD"], "ZA", True), (["All countries", "WLD"], "WORLD", True),
     (["All countries"], "EU", False), (["EU27_2020", "EU member states"], "IT", True),
     (["EU27_2020", "EU member states"], "EU", True), (["EU27_2020", "EU member states"], "GB", False),
     (["EU27_2020", "EU member states", "EFTA countries"], "NO", True),
     (["EU27_2020", "EU member states"], "ZA", False), (["EA", "EU27_2020"], "EA", True),
     (["OWID_WRL"], "WORLD", True), (["IT", "DE"], "DE", True), (["IT", "DE"], "FR", False),
     (["NUTS 1 and NUTS 2 regions"], "IT", True), (["WLD"], None, True)],
)  # fmt: skip
def test_covers(labels: list[str], geo: str | None, expected: bool) -> None:
    assert covers(labels, geo) is expected


def test_unknown_label_is_an_error() -> None:
    with pytest.raises(UnknownCoverageLabel, match="Mars"):
        covered_codes(["EU27_2020", "Mars"])


def test_every_label_in_the_catalog_is_known() -> None:
    """A new coverage label must be added to holdsup/catalog/coverage.py LABELS."""
    catalog = load_catalog(get_settings().catalog_dir)
    for spec in catalog.indicators:
        assert covered_codes(spec.geo_coverage), spec.id
