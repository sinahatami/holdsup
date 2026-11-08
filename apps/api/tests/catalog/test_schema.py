"""Catalog schema and validator."""

import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from holdsup.catalog.load import main as load_main
from holdsup.catalog.schema import CatalogError, IndicatorSpec, Theme, load_catalog
from tests.catalog.helpers import FIXTURE_CATALOG

VALID = yaml.safe_load((FIXTURE_CATALOG / "indicators" / "unemployment_rate.yaml").read_text())


def test_fixture_catalog_loads() -> None:
    catalog = load_catalog(FIXTURE_CATALOG)
    assert catalog.version == "0.0.1-test"
    assert len(catalog.indicators) == 6
    youth = catalog.get("youth_unemployment_rate")
    assert youth.filters == {"sex": "T", "age": "Y15-24", "unit": "PC_ACT"}
    assert youth.last_year is None
    assert "jobless rate for young people" in youth.embedding_text()
    with pytest.raises(KeyError):
        catalog.get("nope")


def test_real_catalog_is_valid() -> None:
    """packages/catalog must always validate (empty until P1.10)."""
    root = Path(__file__).resolve().parents[4] / "packages" / "catalog"
    assert load_catalog(root).version


def test_theme_is_required() -> None:
    without_theme = {k: v for k, v in VALID.items() if k != "theme"}
    with pytest.raises(ValidationError, match="theme"):
        IndicatorSpec.model_validate(without_theme)


def test_real_catalog_lists_every_theme_and_no_unthemed_entry() -> None:
    """The /indicators page groups by theme; an empty theme would be a heading with no entries."""
    root = Path(__file__).resolve().parents[4] / "packages" / "catalog"
    used = {spec.theme for spec in load_catalog(root).indicators}
    assert used == set(Theme)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"aliases": ["a", "b"]}, "at least 3"),
        ({"aliases": ["a", "b", "c", "d", "e", "f"]}, "at most 5"),
        ({"aliases": ["jobless", "Jobless", "x"]}, "duplicates"),
        ({"aliases": ["unemployment rate", "a", "b"]}, "repeats the name"),
        ({"id": "Unemployment-Rate"}, "should match pattern"),
        ({"source": "imf"}, "eurostat"),
        ({"frequency": "weekly"}, "annual"),
        ({"first_year": 2020, "last_year": 2010}, "before first_year"),
        ({"related": ["unemployment_rate"]}, "related to itself"),
        ({"definition": "short"}, "at least 10"),
        ({"geo_coverage": []}, "at least 1"),
        ({"surprise": 1}, "Extra inputs"),
        ({"theme": "sport"}, "population"),
    ],
)
def test_invalid_entries(change: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        IndicatorSpec.model_validate({**VALID, **change})


def make_catalog(tmp_path: Path, entries: dict[str, str], version: str | None = "1.0.0") -> Path:
    (tmp_path / "indicators").mkdir()
    if version is not None:
        (tmp_path / "VERSION").write_text(version)
    for name, text in entries.items():
        (tmp_path / "indicators" / name).write_text(text)
    return tmp_path


def entry(**change: object) -> str:
    return yaml.safe_dump({**VALID, "related": [], **change})


def test_cross_file_problems_are_all_reported(tmp_path: Path) -> None:
    root = make_catalog(
        tmp_path,
        {
            "unemployment_rate.yaml": entry(related=["ghost"]),
            "wrong_name.yaml": entry(id="other_rate", filters={"x": "1"}),
            "broken.yaml": "id: [unclosed",
            "invalid.yaml": entry(id="invalid", aliases=[]),
            "same_series.yaml": entry(id="same_series"),
        },
        version="",
    )
    with pytest.raises(CatalogError) as info:
        load_catalog(root)
    text = str(info.value)
    assert "VERSION" in text
    assert "related indicator 'ghost' does not exist" in text
    assert "file name must be other_rate.yaml" in text
    assert "broken.yaml" in text
    assert "invalid.yaml" in text
    assert "same source series" in text
    assert len(info.value.problems) == 6


def test_duplicate_ids(tmp_path: Path) -> None:
    root = make_catalog(
        tmp_path,
        {"a.yaml": entry(id="a"), "b.yaml": entry(id="a", filters={"age": "Y20-64"})},
    )
    with pytest.raises(CatalogError, match="duplicate id a"):
        load_catalog(root)


def test_cli_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert load_main([str(FIXTURE_CATALOG), "--check"]) == 0
    assert "6 valid entries" in capsys.readouterr().out

    bad = make_catalog(tmp_path, {"x.yaml": "id: [unclosed"})
    assert load_main([str(bad), "--check"]) == 1
    assert "catalog is invalid" in capsys.readouterr().err


def test_copy_of_fixture_catalog_round_trips(tmp_path: Path) -> None:
    shutil.copytree(FIXTURE_CATALOG, tmp_path / "c")
    assert load_catalog(tmp_path / "c") == load_catalog(FIXTURE_CATALOG)


def test_drafts_folder_is_ignored(tmp_path: Path) -> None:
    """packages/catalog/drafts/ holds unfinished entries (e.g. empty aliases); never loaded."""
    root = make_catalog(tmp_path, {"unemployment_rate.yaml": entry()})
    (root / "drafts").mkdir()
    (root / "drafts" / "half_done.yaml").write_text(entry(id="half_done", aliases=[]))
    catalog = load_catalog(root)
    assert [s.id for s in catalog.indicators] == ["unemployment_rate"]


def test_annual_value_is_only_for_monthly_or_quarterly_series() -> None:
    with pytest.raises(ValidationError, match="annual_value is only for monthly or quarterly"):
        IndicatorSpec.model_validate({**VALID, "annual_value": "mean"})
    monthly = IndicatorSpec.model_validate({**VALID, "frequency": "monthly", "annual_value": "end"})
    assert monthly.annual_value is not None and monthly.annual_value.value == "end"
    assert IndicatorSpec.model_validate({**VALID, "frequency": "quarterly"}).annual_value is None


def test_release_lag_defaults_by_frequency() -> None:
    assert IndicatorSpec.model_validate(VALID).lag_months == 12
    monthly = IndicatorSpec.model_validate({**VALID, "frequency": "monthly"})
    assert monthly.lag_months == 1
    assert IndicatorSpec.model_validate({**VALID, "release_lag_months": 18}).lag_months == 18
    with pytest.raises(ValidationError):
        IndicatorSpec.model_validate({**VALID, "release_lag_months": -1})
