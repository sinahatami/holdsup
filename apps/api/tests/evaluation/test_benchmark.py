"""The benchmark file: the real smoke set loads, and a mistake in a label is an error."""

import json
from pathlib import Path
from typing import Any

import pytest
from scripts.evaluation.benchmark import (
    BenchmarkError,
    check_indicators,
    load_benchmark,
    select,
)

from holdsup.config import REPO_ROOT
from holdsup.verdict import Label
from tests.evaluation.helpers import label, text
from tests.pipeline.test_regressions import CATALOG

SMOKE = REPO_ROOT / "eval" / "smoke_claims.jsonl"


def write(path: Path, *lines: dict[str, Any] | str) -> Path:
    path.write_text(
        "\n".join(line if isinstance(line, str) else json.dumps(line) for line in lines) + "\n",
        encoding="utf-8",
    )
    return path


def entry(**over: Any) -> dict[str, Any]:
    claim = {
        "quote": "q",
        "indicator": "unemployment_rate_monthly",
        "geo": "IT",
        "window": ["2015", "2023"],
        "expected": "supported",
        "justification": "j",
    }
    return {"id": "a1", "text": "t", "claims": [claim], **over}


def test_the_smoke_set_loads_and_every_label_is_in_the_catalog() -> None:
    texts = load_benchmark(SMOKE)
    check_indicators(texts, CATALOG)

    assert len(texts) >= 10 and len({t.id for t in texts}) == len(texts)
    assert all(c.expected in set(Label) for t in texts for c in t.claims)
    assert (SMOKE.parent / "VERSION").read_text().strip()


def test_a_window_may_end_at_latest_and_start_at_a_month() -> None:
    texts = load_benchmark(SMOKE)
    windows = {c.window for t in texts for c in t.claims}

    assert ("2014-02", "latest") in windows


def test_every_problem_is_reported_with_its_line(tmp_path: Path) -> None:
    bad_period = entry(id="b")
    bad_period["claims"][0]["window"] = ["15", "2023"]
    bad_label = entry(id="c")
    bad_label["claims"][0]["expected"] = "mostly_true"
    path = write(tmp_path / "claims.jsonl", entry(), bad_period, bad_label, "{not json")

    with pytest.raises(BenchmarkError) as error:
        load_benchmark(path)

    message = str(error.value)
    assert "claims.jsonl:2: claims.0.window" in message and "'15' is not a period" in message
    assert "claims.jsonl:3: claims.0.expected" in message
    assert "claims.jsonl:4" in message


def test_a_misspelt_key_is_an_error_not_a_missing_label(tmp_path: Path) -> None:
    claim = entry()["claims"][0] | {"justificaton": "typo"}
    path = write(tmp_path / "claims.jsonl", entry(claims=[claim]))

    with pytest.raises(BenchmarkError, match="Extra inputs are not permitted"):
        load_benchmark(path)


def test_ids_are_unique_and_a_text_needs_a_claim(tmp_path: Path) -> None:
    path = write(tmp_path / "claims.jsonl", entry(), entry(), entry(id="empty", claims=[]))

    with pytest.raises(BenchmarkError) as error:
        load_benchmark(path)

    assert "duplicate id 'a1'" in str(error.value)
    assert "empty has no labelled claims" in str(error.value)


def test_blank_lines_are_skipped(tmp_path: Path) -> None:
    path = write(tmp_path / "claims.jsonl", entry(), "", "   ", entry(id="b"))

    assert [t.id for t in load_benchmark(path)] == ["a1", "b"]


def test_an_indicator_the_catalog_lacks_is_an_error() -> None:
    texts = [
        text("a", "x", label(indicator="no_such_indicator")),
        text("b", "y", label(indicator=None)),
    ]

    with pytest.raises(
        BenchmarkError, match="a: indicator 'no_such_indicator' is not in the catalog"
    ):
        check_indicators(texts, CATALOG)


def test_no_indicator_is_fine_for_a_claim_the_catalog_cannot_check() -> None:
    check_indicators([text("b", "y", label(indicator=None, expected=Label.CANT_CHECK))], CATALOG)


def test_the_dev_split_includes_texts_with_no_split_and_never_the_test_split() -> None:
    texts = [text("a"), text("b", split="dev"), text("c", split="test")]

    assert [t.id for t in select(texts, "dev")] == ["a", "b"]
    assert [t.id for t in select(texts, "test")] == ["c"]
    assert [t.id for t in select(texts, "all")] == ["a", "b", "c"]
