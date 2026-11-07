"""Catalog entry schema and validator. One YAML file per indicator: `<id>.yaml`."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$", max_length=100)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Source(StrEnum):
    EUROSTAT = "eurostat"
    WORLDBANK = "worldbank"
    OWID = "owid"
    DATACOMMONS = "datacommons"


class Frequency(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"


class AnnualValue(StrEnum):
    """How a year's value is made from a monthly or quarterly series."""

    MEAN = "mean"  # the average of the year's months or quarters (rates, shares, yoy growth)
    END = "end"  # the last month or quarter of the year (stocks such as debt to GDP)


class IndicatorSpec(BaseModel):
    """One curated indicator. Field meanings: docs/spec.md "Data sources and indicator catalog"."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Slug
    source: Source
    source_code: Text
    name: Text
    aliases: list[Text] = Field(min_length=3, max_length=5)
    definition: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=500)
    ]
    unit: Text
    frequency: Frequency
    geo_coverage: list[Text] = Field(min_length=1)
    first_year: int = Field(ge=1700, le=2100)
    last_year: int | None = Field(default=None, ge=1700, le=2100)  # null = still updated
    related: list[Slug] = Field(default_factory=list)
    # Fixed query filters for the adapter (not geo/time), e.g. Eurostat {sex: T, unit: PC_ACT}.
    filters: dict[str, str | list[str]] = Field(default_factory=dict)
    # Monthly or quarterly series only: how code makes a year's value for a claim about a whole
    # year. Null means no yearly value can be made (e.g. growth on the previous quarter).
    annual_value: AnnualValue | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.last_year is not None and self.last_year < self.first_year:
            raise ValueError("last_year is before first_year")
        if self.frequency is Frequency.ANNUAL and self.annual_value is not None:
            raise ValueError("annual_value is only for monthly or quarterly series")
        lowered = [a.lower() for a in self.aliases]
        if len(set(lowered)) != len(lowered):
            raise ValueError("aliases contain duplicates")
        if self.name.lower() in lowered:
            raise ValueError("an alias repeats the name")
        if self.id in self.related:
            raise ValueError("an indicator cannot be related to itself")
        return self

    def embedding_text(self) -> str:
        """What gets embedded for search: name, aliases, definition."""
        return f"{self.name}. Also called: {'; '.join(self.aliases)}. {self.definition}"


class CatalogError(Exception):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("catalog is invalid:\n" + "\n".join(f"  - {p}" for p in problems))


class Catalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    indicators: tuple[IndicatorSpec, ...]

    def get(self, indicator_id: str) -> IndicatorSpec:
        for spec in self.indicators:
            if spec.id == indicator_id:
                return spec
        raise KeyError(indicator_id)


def load_catalog(root: Path) -> Catalog:
    """Validate every `indicators/*.yaml` under `root`; report all problems at once."""
    version_file = root / "VERSION"
    problems: list[str] = []
    version = version_file.read_text().strip() if version_file.exists() else ""
    if not version:
        problems.append(f"{version_file}: missing or empty")

    specs: list[IndicatorSpec] = []
    for path in sorted((root / "indicators").glob("*.yaml")):
        try:
            with path.open(encoding="utf-8") as f:
                spec = IndicatorSpec.model_validate(yaml.safe_load(f))
        except (yaml.YAMLError, ValidationError) as exc:
            problems.append(f"{path.name}: {exc}")
            continue
        if path.stem != spec.id:
            problems.append(f"{path.name}: file name must be {spec.id}.yaml")
        specs.append(spec)

    ids = [s.id for s in specs]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"duplicate id {dup}")
    known = set(ids)
    for spec in specs:
        for rel in spec.related:
            if rel not in known:
                problems.append(f"{spec.id}: related indicator {rel!r} does not exist")
    keys = [(s.source, s.source_code, tuple(sorted(s.filters.items(), key=str))) for s in specs]
    if len(set(map(str, keys))) != len(keys):
        problems.append("two entries point at the same source series and filters")

    if problems:
        raise CatalogError(problems)
    return Catalog(version=version, indicators=tuple(specs))
