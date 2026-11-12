"""The command: what it refuses, what it writes, and the gate's exit codes end to end."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from scripts.evaluation.cli import RigFactory, main
from scripts.evaluation.report import Report
from scripts.evaluation.run import Rig

from holdsup.catalog.schema import Catalog
from holdsup.router import RouterConfig, Use
from holdsup.verdict import Label, Tolerances
from tests.evaluation.helpers import FALL, fall_script, label, make_rig, text


def factory(config_seen: list[RouterConfig] | None = None) -> RigFactory:
    """A rig of fakes, freshly scripted for every run."""

    @asynccontextmanager
    async def build(
        catalog: Catalog, config: RouterConfig, tolerances: Tolerances, use: Use
    ) -> AsyncIterator[Rig]:
        if config_seen is not None:
            config_seen.append(config)
        rig, _, _ = make_rig(fall_script())
        yield rig

    return build


def benchmark(tmp_path: Path, *texts: dict[str, Any], version: str | None = "0.1.0") -> Path:
    claims = tmp_path / "claims.jsonl"
    claims.write_text("\n".join(json.dumps(t) for t in texts) + "\n", encoding="utf-8")
    if version is not None:
        (tmp_path / "VERSION").write_text(version + "\n", encoding="utf-8")
    return claims


def entry(
    id: str = "r001", *, expected: Label = Label.SUPPORTED, split: str | None = None
) -> dict[str, Any]:  # Any: one benchmark line as JSON, which the tests edit key by key
    item = text(id, FALL, label(expected=expected), split=split)
    return item.model_dump(mode="json", exclude_none=True)


def run(tmp_path: Path, claims: Path, *flags: str, fake: RigFactory | None = None) -> int:
    argv = ["--claims", str(claims), "--out-dir", str(tmp_path / "out"), *flags]
    return main(argv, fake or factory())


def test_a_run_writes_the_report_and_says_how_it_went(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run(tmp_path, benchmark(tmp_path, entry()))

    out = capsys.readouterr()
    assert code == 0
    assert "1 claims in 1 texts: verdict accuracy 100%" in out.out
    assert "[1/1] r001: 1/1 verdicts right" in out.err  # progress goes to stderr
    report = Report.model_validate_json((tmp_path / "out" / "dev.json").read_text())
    assert (report.versions.eval, report.benchmark, report.split) == (
        "0.1.0",
        "claims.jsonl",
        "dev",
    )
    assert report.provider == "router" and report.metrics.verdict.accuracy.rate == 1.0
    assert (tmp_path / "out" / "dev.md").exists()


def test_the_held_out_split_is_refused_unless_the_run_is_final(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claims = benchmark(tmp_path, entry(split="test"))

    assert run(tmp_path, claims, "--split", "test") == 2
    assert "held out for the final report" in capsys.readouterr().err
    assert run(tmp_path, claims, "--split", "all") == 2
    assert not (tmp_path / "out").exists()  # nothing ran

    assert run(tmp_path, claims, "--split", "test", "--final") == 0
    assert (tmp_path / "out" / "test.json").exists()


def test_the_dev_run_never_touches_a_test_text(tmp_path: Path) -> None:
    claims = benchmark(tmp_path, entry("dev1"), entry("held", split="test"))

    assert run(tmp_path, claims) == 0

    report = Report.model_validate_json((tmp_path / "out" / "dev.json").read_text())
    assert [t.id for t in report.texts] == ["dev1"]


def test_an_empty_split_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    claims = benchmark(tmp_path, entry(split="test"))

    assert run(tmp_path, claims) == 2
    assert "no texts in the dev split" in capsys.readouterr().err


def test_limit_runs_only_the_first_texts(tmp_path: Path) -> None:
    claims = benchmark(tmp_path, entry("a"), entry("b"))

    assert run(tmp_path, claims, "--limit", "1", "--name", "quick") == 0

    report = Report.model_validate_json((tmp_path / "out" / "quick.json").read_text())
    assert [t.id for t in report.texts] == ["a"]


def test_a_bad_benchmark_is_reported_and_nothing_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = entry()
    bad["claims"][0]["expected"] = "mostly_true"

    assert run(tmp_path, benchmark(tmp_path, bad)) == 2
    assert "claims.jsonl:1: claims.0.expected" in capsys.readouterr().err


def test_a_label_for_a_statistic_the_catalog_lacks_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    item = entry()
    item["claims"][0]["indicator"] = "no_such_indicator"

    assert run(tmp_path, benchmark(tmp_path, item)) == 2
    assert "indicator 'no_such_indicator' is not in the catalog" in capsys.readouterr().err


def test_a_benchmark_without_a_version_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path, benchmark(tmp_path, entry(), version=None)) == 2
    assert "needs a version" in capsys.readouterr().err


def test_a_missing_benchmark_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path, tmp_path / "nope.jsonl") == 2
    assert "nope.jsonl" in capsys.readouterr().err


def test_a_per_provider_run_forces_every_step_onto_that_provider(tmp_path: Path) -> None:
    seen: list[RouterConfig] = []

    code = run(
        tmp_path, benchmark(tmp_path, entry()), "--provider", "groq-gpt-oss-120b",
        fake=factory(seen),
    )  # fmt: skip

    assert code == 0
    assert {names for names in seen[0].steps.values()} == {("groq-gpt-oss-120b",)}
    report = Report.model_validate_json(
        (tmp_path / "out" / "dev.groq-gpt-oss-120b.json").read_text()
    )
    assert report.provider == "groq-gpt-oss-120b"
    assert set(report.steps["extract"]) == {"groq-gpt-oss-120b/openai/gpt-oss-120b"}


def test_an_unknown_provider_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(tmp_path, benchmark(tmp_path, entry()), "--provider", "nope") == 2
    assert "unknown provider 'nope'; known: groq-gpt-oss-120b" in capsys.readouterr().err


def test_gemini_runs_only_when_the_run_says_it_is_offline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claims = benchmark(tmp_path, entry())

    assert run(tmp_path, claims, "--provider", "gemini-flash") == 2
    assert "may only run offline jobs: pass --use offline" in capsys.readouterr().err
    assert run(tmp_path, claims, "--provider", "gemini-flash", "--use", "offline") == 0


@pytest.mark.parametrize(
    "flags",
    [
        ("--gate", "--update-baseline"),
        ("--gate", "--limit", "1"),
        ("--update-baseline", "--provider", "groq-gpt-oss-120b"),
    ],
)
def test_the_gate_only_compares_whole_router_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flags: tuple[str, ...]
) -> None:
    assert run(tmp_path, benchmark(tmp_path, entry()), *flags) == 2
    assert capsys.readouterr().err


def test_the_gate_from_no_baseline_to_a_regression(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claims = benchmark(tmp_path, entry())

    # No baseline yet: the gate cannot judge, and says how to make one.
    assert run(tmp_path, claims, "--gate") == 3
    assert "No baseline" in capsys.readouterr().err

    # Accept this run. It writes baseline.json beside the claims, and does not gate.
    assert run(tmp_path, claims, "--update-baseline") == 0
    saved = json.loads((tmp_path / "baseline.json").read_text())
    assert (saved["verdict_accuracy"], saved["eval"], saved["benchmark"]) == (
        1.0,
        "0.1.0",
        "claims.jsonl",
    )

    # The same run passes.
    assert run(tmp_path, claims, "--gate") == 0
    assert "no change" in capsys.readouterr().out

    # The same pipeline against a label it no longer meets: down 100 points.
    benchmark(tmp_path, entry(expected=Label.NOT_SUPPORTED))
    assert run(tmp_path, claims, "--gate") == 1
    assert "down 100.0 points" in capsys.readouterr().err

    # A change to the benchmark without a new version cannot be compared either way.
    (tmp_path / "VERSION").write_text("0.2.0\n")
    assert run(tmp_path, claims, "--gate") == 3
    assert "--update-baseline" in capsys.readouterr().err


def test_a_baseline_cannot_come_from_a_run_that_judged_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    @asynccontextmanager
    async def no_keys(
        catalog: Catalog, config: RouterConfig, tolerances: Tolerances, use: Use
    ) -> AsyncIterator[Rig]:
        rig, _, _ = make_rig([], keys=set())
        yield rig

    assert run(tmp_path, benchmark(tmp_path, entry()), "--update-baseline", fake=no_keys) == 2
    assert "no judged claim" in capsys.readouterr().err
    assert not (tmp_path / "baseline.json").exists()
