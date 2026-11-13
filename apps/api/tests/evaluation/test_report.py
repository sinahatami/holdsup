"""The report: stamped, complete enough for the /eval page, and free of raw text."""

from pathlib import Path

from scripts.evaluation.meter import Call
from scripts.evaluation.report import Report, markdown, step_models, write_report
from scripts.evaluation.score import score_text, summarize

from holdsup.verdict import Label
from tests.evaluation.helpers import label, make_report, output, result, text
from tests.router.fakes import config, provider


def test_the_report_names_the_provider_and_model_behind_each_step() -> None:
    cfg = config(provider("a"), provider("b"), steps={"extract": ["a", "b"], "match": ["b"]})

    assert step_models(cfg) == {"extract": ["a/a-model", "b/b-model"], "match": ["b/b-model"]}


def test_a_report_is_stamped_with_every_version_it_came_from() -> None:
    report = make_report(3, 4)

    v = report.versions
    assert (v.app, v.eval, v.tolerances) == ("0.0.0+abc1234", "0.1.0", 5)
    assert v.catalog and report.steps["extract"] == ["fake/fake-model"]
    assert report.created_at.isoformat().startswith("2026-11-12T09:30:00")


def test_json_and_markdown_are_written_and_the_json_reads_back(tmp_path: Path) -> None:
    report = make_report(3, 4)

    json_path, md_path = write_report(report, tmp_path / "reports")

    assert (json_path.name, md_path.name) == ("smoke.json", "smoke.md")
    assert Report.model_validate_json(json_path.read_text()) == report
    assert md_path.read_text().startswith("# Evaluation: smoke")


def test_the_report_holds_ids_labels_and_reasons_but_no_benchmark_text(tmp_path: Path) -> None:

    body = "A-DISTINCTIVE-PASTED-SENTENCE-THAT-MUST-NOT-BE-COPIED"
    item = text("t9", body, label())
    outcome = score_text(item, output(result()), {}, seconds=1, model_calls=1)
    report = make_report(1, 1).model_copy(
        update={"texts": [outcome], "metrics": summarize([outcome], [])}
    )

    json_path, md_path = write_report(report, tmp_path)

    assert body not in json_path.read_text() and body not in md_path.read_text()
    assert '"text_id": "t9"' in json_path.read_text()


def test_the_markdown_shows_each_step_the_confusion_matrix_and_the_cost() -> None:
    md = markdown(make_report(3, 4))

    assert "Benchmark `smoke_claims.jsonl` (dev split) at eval 0.1.0: 4 texts, 4 labelled" in md
    assert "App 0.0.0+abc1234" in md and "tolerances v5" in md
    assert "| Verdict | Accuracy, end to end | 75.0% (3/4) |" in md
    assert "| Matching | Top-1 (the labelled statistic picked) | 100.0% (4/4) |" in md
    assert "expected \\ answered" in md and "| supported | 3 | 0 | 1 |" in md
    assert "## Cost" in md and "0 model calls (0 failed)" in md  # no meter calls were fed in


def test_a_provider_that_reached_its_daily_limit_is_named_under_the_cost() -> None:
    spent = Call("plan", "groq-x", "m", False, 40.0, error="RateLimited", daily_limit=True)

    md = markdown(make_report(3, 4, calls=[spent]))

    assert "- Daily limit reached: groq-x. The router moved on to the next choice" in md
    assert "Daily limit" not in markdown(make_report(3, 4))


def test_a_wrong_verdict_is_listed_with_the_step_that_broke_and_its_reason() -> None:
    md = markdown(make_report(3, 4))

    assert "First step that went wrong: verdict 1." in md
    assert (
        "| t3#1 | supported | not_supported | verdict | not_supported because of the numbers. |"
        in md
    )


def test_a_run_with_no_wrong_verdict_says_so() -> None:
    assert "None." in markdown(make_report(4, 4))


def test_claims_left_out_of_the_figures_are_called_out() -> None:
    md = markdown(make_report(3, 3, not_run=1))

    assert "1 of 4 claims are left out of the accuracy figures" in md
    assert "1 in 1 text(s) the router could not serve" in md
    assert "left out" not in markdown(make_report(3, 3))


def test_a_per_provider_run_says_every_step_was_on_that_provider() -> None:
    assert "every step on groq-gpt-oss-120b" in markdown(
        make_report(3, 4, provider_name="groq-gpt-oss-120b")
    )


def test_a_table_cell_cannot_break_the_table() -> None:

    item = text("t1", "x", label())
    bad = result(got=Label.NOT_SUPPORTED)
    bad.verdict.reason = "a | b\nand c"
    outcome = score_text(item, output(bad), {}, seconds=1, model_calls=1)
    report = make_report(0, 1).model_copy(
        update={"texts": [outcome], "metrics": summarize([outcome], [])}
    )

    assert "a \\| b and c" in markdown(report)
