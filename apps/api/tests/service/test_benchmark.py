"""What /eval reads: the committed reports, joined into a head-to-head. Reports here are built
in a temporary folder with the evaluation helpers; the repository's own reports are not read."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from scripts.evaluation.meter import Call
from scripts.evaluation.report import Report, write_report

from holdsup.config import get_settings
from holdsup.main import create_app
from holdsup.service.benchmark import SKIPPED_REPORTS, read_benchmark
from tests.evaluation.helpers import make_report

LABELS = {"fake": "Fake model (test)"}


def put(folder: Path, report: Report, name: str, **changes: object) -> None:
    write_report(report.model_copy(update={"name": name, **changes}), folder)


def folders(tmp_path: Path) -> tuple[Path, Path]:
    reports, ml = tmp_path / "eval" / "reports", tmp_path / "ml"
    reports.mkdir(parents=True)
    (tmp_path / "eval" / "VERSION").write_text("0.3.0\n", encoding="utf-8")
    return reports, ml


def test_a_head_to_head_counts_the_claims_both_could_be_scored_on(tmp_path: Path) -> None:
    reports, ml = folders(tmp_path)
    put(reports, make_report(1, 2), "dev")  # t0 right, t1 wrong
    put(reports, make_report(2, 2, not_run=1), "dev.chatbot", kind="chatbot")  # n0 not served

    bench = read_benchmark(reports, ml, LABELS)

    [cmp] = bench.comparisons
    assert cmp.split == "dev" and cmp.claims == 2  # n0 was not scored: it is in neither figure
    assert (cmp.both_right, cmp.only_chatbot_right, cmp.only_holdsup_right, cmp.both_wrong) == (
        1,
        1,
        0,
        0,
    )
    assert (cmp.holdsup_right.hits, cmp.chatbot_right.hits, cmp.holdsup_right.total) == (1, 2, 2)
    assert cmp.chatbot.left_out == 1 and cmp.holdsup.left_out == 0
    assert bench.eval_version == "0.3.0"


def test_where_holdsup_loses_is_listed_with_the_step_that_broke(tmp_path: Path) -> None:
    reports, ml = folders(tmp_path)
    ours = make_report(1, 2)
    put(reports, ours, "dev")
    put(reports, make_report(2, 2), "dev.chatbot", kind="chatbot")

    [cmp] = read_benchmark(reports, ml, LABELS).comparisons

    [loss] = cmp.losses
    assert loss.text_id == "t1" and loss.expected == "supported" and loss.chatbot == "supported"
    assert loss.holdsup == "not_supported"
    assert loss.broke_at == "verdict" and loss.reason
    wrong = sum(ours.metrics.failures.values())
    assert [(c.step, c.wrong, c.share) for c in cmp.holdsup.failure_causes] == [
        (step, n, round(n / wrong, 4)) for step, n in ours.metrics.failures.items()
    ]


def test_every_run_is_listed_with_the_models_that_answered_by_their_readable_names(
    tmp_path: Path,
) -> None:
    reports, ml = folders(tmp_path)
    calls = [Call("extract", "fake", "m-1", True, 10.0), Call("plan", "fake", "m-1", True, 10.0)]
    put(reports, make_report(1, 1, calls=calls), "dev")
    put(reports, make_report(1, 1), "dev.fake", provider="fake")
    put(reports, make_report(1, 1), "dev.chatbot", kind="chatbot")
    put(reports, make_report(1, 1), "smoke")  # the CI gate's subset: not a result to publish

    runs = read_benchmark(reports, ml, LABELS).runs

    assert [r.name for r in runs] == ["dev", "dev.fake", "dev.chatbot"]  # pipeline runs first
    assert [(m.provider, m.label, m.calls) for m in runs[0].models] == [
        ("fake", "Fake model (test)", 2)
    ]
    assert "smoke" in SKIPPED_REPORTS


def test_a_split_with_only_one_side_has_no_comparison_and_a_broken_file_is_skipped(
    tmp_path: Path,
) -> None:
    reports, ml = folders(tmp_path)
    put(reports, make_report(1, 1), "dev")
    (reports / "old.json").write_text('{"schema_version": 0}', encoding="utf-8")
    (reports / "cut.json").write_text('{"name": "x"', encoding="utf-8")

    bench = read_benchmark(reports, ml, LABELS)

    assert bench.comparisons == [] and [r.name for r in bench.runs] == ["dev"]


def test_nothing_committed_yet_is_an_empty_benchmark_not_an_error(tmp_path: Path) -> None:
    bench = read_benchmark(tmp_path / "none", tmp_path / "ml", LABELS)

    assert (bench.eval_version, bench.comparisons, bench.runs, bench.models) == (None, [], [], [])


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_the_model_reports_become_small_tables_with_the_notes_that_matter(tmp_path: Path) -> None:
    reports, ml = folders(tmp_path)
    cell = {"claims": 9, "top1": 0.5, "recall_at_8": 0.9, "mrr_at_8": 0.6}
    write_json(
        ml / "reranker" / "reports" / "report.json",
        {
            "created": "2026-11-13",
            "cross_validation": {
                k: {"all": cell, "unseen": {**cell, "top1": 0.25}}
                for k in ("embedding", "base", "reranker")
            },
            "margins": [{"threshold": 0.5, "coverage": 0.52, "accuracy": 0.964}],
        },
    )
    write_json(
        ml / "confidence" / "reports" / "report.json",
        {
            "created": "2026-11-15",
            "data": {"rows": 80, "wrong": 13},
            "cross_validation": {
                "beats_base_rate": False,
                "boosting_clearly_better": True,
                "models": [
                    {
                        "name": "base_rate",
                        "label": "Base rate",
                        "brier": 0.1384,
                        "log_loss": 0.45,
                        "auc": None,
                    },
                    {
                        "name": "logistic",
                        "label": "Logistic",
                        "brier": 0.1395,
                        "log_loss": 0.4537,
                        "auc": 0.5614,
                    },
                ],
            },
            "limitations": ["About a hundred rows."],
        },
    )

    reranker, confidence = read_benchmark(reports, ml, LABELS).models

    assert reranker.table.rows[0] == ["Embedding search alone", "50.0%", "25.0%", "90.0%", "0.600"]
    assert "covers 52.0% of dev claims" in reranker.notes[1] and "96.4%" in reranker.notes[1]
    assert confidence.table.rows == [
        ["Base rate", "0.1384", "0.4500", "n/a"],
        ["Logistic", "0.1395", "0.4537", "0.561"],
    ]
    assert any(n.startswith("Not served") for n in confidence.notes)
    assert any("Gradient boosting" in n for n in confidence.notes)
    assert confidence.notes[-1] == "About a hundred rows."


def test_a_model_report_that_cannot_be_read_is_left_out(tmp_path: Path) -> None:
    reports, ml = folders(tmp_path)
    (ml / "reranker" / "reports").mkdir(parents=True)
    (ml / "reranker" / "reports" / "report.json").write_text("[1, 2]", encoding="utf-8")

    assert read_benchmark(reports, ml, LABELS).models == []


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    reports, ml = folders(tmp_path)
    put(reports, make_report(1, 2), "dev")
    put(reports, make_report(2, 2), "dev.chatbot", kind="chatbot")
    monkeypatch.setenv("REPORTS_DIR", str(reports))
    monkeypatch.setenv("ML_DIR", str(ml))
    get_settings.cache_clear()
    with TestClient(create_app()) as http:
        yield http
    get_settings.cache_clear()


def test_the_endpoint_serves_the_head_to_head(api: TestClient) -> None:
    response = api.get("/v1/eval")

    assert response.status_code == 200
    body = response.json()
    assert body["eval_version"] == "0.3.0"
    assert body["comparisons"][0]["only_chatbot_right"] == 1
    assert [r["name"] for r in body["runs"]] == ["dev", "dev.chatbot"]
