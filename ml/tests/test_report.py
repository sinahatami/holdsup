"""report.json, report.md and the model card, from a synthetic cross-validation."""

from dataclasses import asdict
from pathlib import Path

import pytest

from holdsup.catalog.schema import Catalog
from reranker.dataset import build_groups
from reranker.experiment import BASE, EMBEDDING, RERANKER, CrossValidation, Hyper
from reranker.metrics import Ranked
from reranker.paraphrase import Paraphrase
from reranker.report import (
    Export,
    Inputs,
    Report,
    Variant,
    build_report,
    render_card,
    render_markdown,
    write_report,
)
from reranker.scorer import Latency
from tests.helpers import DEBT, UNEMPLOYMENT, YOUTH, FixedSearch, claims


def cv() -> CrossValidation:
    out = CrossValidation(fold_sizes=[2, 1], training_pairs=[10, 12])
    rows = {
        EMBEDDING: [("a#1", "x", "yx", [0.9, 0.8], True), ("b#1", "x", "xy", [0.9, 0.1], False)],
        BASE: [("a#1", "x", "xy", [0.6, 0.5], True), ("b#1", "x", "yx", [0.6, 0.5], False)],
        RERANKER: [("a#1", "x", "xy", [0.9, 0.1], True), ("b#1", "x", "xy", [0.7, 0.6], False)],
    }
    for ranker, rs in rows.items():
        for key, gold, ids, scores, seen in rs:
            out.add(ranker, Ranked(key, gold, tuple(ids), tuple(scores), seen))
    out.add(RERANKER, Ranked("c#1", None, ("x", "y"), (0.03, 0.01), False))
    return out


def report(catalog: Catalog) -> Report:
    bench = claims()
    paraphrases = [
        Paraphrase(claim="d1#1", text="Italian joblessness: 8%", provider="groq", model="m1"),
        Paraphrase(claim="d1#1", text="Italy, 8% out of work", provider="gemini", model="m2"),
    ]
    search = FixedSearch([(UNEMPLOYMENT, 0.9), (YOUTH, 0.5)])
    return build_report(
        Inputs(
            hyper=asdict(Hyper()),
            claims=bench,
            groups=build_groups(bench, paraphrases, catalog, search),
            paraphrases=paraphrases,
            training_pairs=99,
            cv=cv(),
            eval_version="0.2.0",
            catalog_version=catalog.version,
            paraphrases_sha256="f" * 64,
            created="2026-11-13",
        )
    )


def test_the_report_counts_data_from_the_inputs(catalog: Catalog) -> None:
    r = report(catalog)
    d = r.data
    assert (d.dev_claims, d.with_indicator, d.paraphrases, d.queries) == (5, 4, 2, 7)
    assert d.indicators == len({UNEMPLOYMENT, YOUTH, DEBT, "life_expectancy"})
    assert d.paraphrase_models == {"groq/m1": 1, "gemini/m2": 1}
    assert d.positives_added == 2  # the DEBT and LIFE claims: not in the pool
    assert (d.folds, d.fold_sizes, d.training_pairs) == (2, [2, 1], 99)
    assert r.training_claims == ["d1#1", "d2#1", "d2#2", "d3#1", "d4#1"]
    assert r.export is None


def test_the_report_summarizes_each_ranker_by_seen_and_unseen(catalog: Catalog) -> None:
    r = report(catalog)
    assert list(r.cross_validation) == [EMBEDDING, BASE, RERANKER]
    assert r.cross_validation[EMBEDDING]["all"].top1 == 0.5
    assert r.cross_validation[RERANKER]["all"].top1 == 1.0
    assert r.cross_validation[RERANKER]["all"].claims == 2  # c#1 has no statistic
    assert r.cross_validation[RERANKER]["seen"].claims == 1
    assert r.cross_validation[BASE]["unseen"].mrr_at_8 == 0.5
    assert r.no_indicator.claims == 1 and r.no_indicator.highest_probability == 0.03
    first = r.margins[0]
    assert first.threshold == 0.1 and first.answered == 1 and first.correct == 1


def test_markdown_and_card_show_computed_numbers(catalog: Catalog) -> None:
    lat = Latency(
        threads=2, claims=3, candidates_per_claim=8.0, p50_ms=12.5, p95_ms=20.0, mean_ms=13
    )
    r = report(catalog).model_copy(
        update={
            "export": Export(
                max_abs_diff=1e-5,
                variants=[
                    Variant(name="fp32", sha256="a", megabytes=91.0, latency=lat),
                    Variant(name="int8", sha256="b", megabytes=23.0, latency=lat),
                ],
                int8_top1_agreement=0.99,
                int8_max_probability_diff=0.05,
            )
        }
    )
    md = render_markdown(r)
    assert "| All | Embedding search alone | 2 | 50.0% | 100.0% | 0.750 |" in md
    assert "| All | Fine-tuned reranker | 2 | 100.0% | 100.0% | 1.000 |" in md
    assert "| int8 | 23.0 MB | 12.5 ms | 20.0 ms |" in md
    assert "99.0% of the dev quotes" in md
    card = render_card(r)
    assert card.startswith("---\nlanguage: en\n")
    assert f"base_model: {Hyper().base_model}" in card
    assert "top-1 100.0% against 50.0% for the embedding search alone" in card
    assert "Not measured" in render_markdown(report(catalog))


def test_write_report_writes_json_markdown_and_card_copies(
    catalog: Catalog, tmp_path: Path
) -> None:
    r = report(catalog)
    write_report(r, tmp_path / "reports", tmp_path / "card.md", tmp_path / "model" / "README.md")
    again = Report.model_validate_json((tmp_path / "reports" / "report.json").read_text())
    assert again == r
    assert (tmp_path / "reports" / "report.md").read_text().startswith("# Indicator reranker")
    assert (tmp_path / "card.md").read_text() == (tmp_path / "model" / "README.md").read_text()


@pytest.mark.parametrize("value, text", [(None, "n/a"), (0.1234, "12.3%")])
def test_percent_format(value: float | None, text: str) -> None:
    from reranker.report import pct

    assert pct(value) == text


def test_the_committed_card_names_the_hub_repo_the_api_pins() -> None:
    from holdsup.ml.reranker import load_pin
    from reranker import MODEL_CARD

    card = MODEL_CARD.read_text(encoding="utf-8")
    assert f'CrossEncoder("{load_pin().repo}")' in card and "<hub-owner>" not in card
