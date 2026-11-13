"""The benchmark as the reranker needs it: one sentence per labelled claim, with its split.

The file's strict validation is the evaluation runner's (apps/api/scripts/evaluation). This
reads only what training uses, and keeps the split on every claim so code can refuse the
held-out ones instead of trusting that a caller filtered them.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

Split = Literal["dev", "test"]


class _Claim(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    quote: str
    indicator: str | None
    geo: str | None


class _Text(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    text: str
    split: Split | None = None
    claims: tuple[_Claim, ...]


@dataclass(frozen=True)
class Claim:
    key: str  # "<text id>#<n>", n from 1: how the evaluation reports name a claim
    text_id: str
    text: str  # the whole text the claim was read from
    quote: str
    indicator: str | None  # None: the catalog has nothing for it
    geo: str | None
    split: Split

    @property
    def group(self) -> str:
        """Its cross-validation group: claims about one statistic in one place stay together,
        so a sentence and its variants (another number or year) never sit on both sides."""
        return f"{self.indicator}@{self.geo}" if self.indicator else self.key


def parse_claims(lines: Sequence[str]) -> list[Claim]:
    out: list[Claim] = []
    for line in lines:
        if not line.strip():
            continue
        text = _Text.model_validate_json(line)
        for n, c in enumerate(text.claims, start=1):
            out.append(
                Claim(
                    key=f"{text.id}#{n}",
                    text_id=text.id,
                    text=text.text,
                    quote=c.quote,
                    indicator=c.indicator,
                    geo=c.geo,
                    split=text.split or "dev",  # no split counts as dev (eval/README.md)
                )
            )
    return out


def load_claims(path: Path) -> list[Claim]:
    return parse_claims(path.read_text(encoding="utf-8").splitlines())


def dev(claims: Sequence[Claim]) -> list[Claim]:
    return [c for c in claims if c.split == "dev"]
