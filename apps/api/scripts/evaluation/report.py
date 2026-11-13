"""The report of one run: JSON for the /eval page (P4.6) and Markdown for people.

Every report is stamped with what produced it: app, catalog, tolerances and benchmark
versions, and the provider and model behind each step. It carries claim ids, labels, the
pipeline's verdicts and the code-written reasons, never a raw model answer or the benchmark's
full texts.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from holdsup.router import RouterConfig
from scripts.evaluation.score import (
    MISSED,
    ClaimOutcome,
    Metrics,
    Rate,
    TextOutcome,
)

SCHEMA_VERSION = 1
ROUTER = "router"  # a run on each step's whole preference list, not one provider


class Stamp(BaseModel):
    app: str
    catalog: str
    tolerances: int
    eval: str  # eval/VERSION


class Report(BaseModel):
    schema_version: int = SCHEMA_VERSION
    name: str  # "smoke", "dev", "test", "dev.groq-gpt-oss-120b"
    created_at: datetime
    benchmark: str  # the claims file's name
    split: str
    provider: str  # ROUTER, or the one provider every step was forced onto
    use: str
    versions: Stamp
    # What each step could use, first choice first: "provider/model".
    steps: dict[str, list[str]]
    metrics: Metrics
    texts: list[TextOutcome]


def step_models(config: RouterConfig) -> dict[str, list[str]]:
    by_name = {p.name: p for p in config.providers}
    return {
        step: [f"{name}/{by_name[name].model}" for name in names]
        for step, names in config.steps.items()
    }


def build_report(
    *,
    name: str,
    benchmark: str,
    split: str,
    provider: str,
    use: str,
    versions: Stamp,
    config: RouterConfig,
    metrics: Metrics,
    texts: Sequence[TextOutcome],
    now: datetime | None = None,
) -> Report:
    return Report(
        name=name,
        created_at=(now or datetime.now(UTC)).replace(microsecond=0),
        benchmark=benchmark,
        split=split,
        provider=provider,
        use=use,
        versions=versions,
        steps=step_models(config),
        metrics=metrics,
        texts=list(texts),
    )


def write_report(report: Report, out_dir: Path) -> tuple[Path, Path]:
    """Write `<name>.json` and `<name>.md` into `out_dir`; returns both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, md_path = out_dir / f"{report.name}.json", out_dir / f"{report.name}.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    return json_path, md_path


# --- Markdown --------------------------------------------------------------------------------


def pct(rate: Rate) -> str:
    """ "80.0% (12/15)", or "n/a" when nothing was measured."""
    if rate.rate is None:
        return "n/a"
    return f"{rate.rate * 100:.1f}% ({rate.hits}/{rate.total})"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return lines + [""]


def markdown(report: Report) -> str:
    m, v = report.metrics, report.versions
    out = [
        f"# Evaluation: {report.name}",
        "",
        (
            f"- Benchmark `{report.benchmark}` ({report.split} split) at eval {v.eval}: "
            f"{m.texts} texts, {m.labelled_claims} labelled claims, {m.extracted_claims} extracted."
        ),
        f"- App {v.app}, catalog {v.catalog}, tolerances v{v.tolerances}.",
        f"- Providers: {_providers(report)}. Run {report.created_at:%Y-%m-%d %H:%M} UTC.",
        "",
    ]
    out += _excluded(m)
    out += ["## Per step", ""]
    out += _table(
        ["Step", "Metric", "Result"],
        [
            ["Extraction", "Precision (extracted claims that are labelled)", pct(m.extraction.precision)],
            ["", "Recall (labelled claims found)", pct(m.extraction.recall)],
            ["", "Place right", pct(m.extraction.geo)],
            ["", "Start right", pct(m.extraction.start)],
            ["", "End right", pct(m.extraction.end)],
            ["Matching", "Top-1 (the labelled statistic picked)", pct(m.matching.top1)],
            ["", "Recall@8 of the search alone", pct(m.matching.recall_at_8)],
            ["Verdict", "Accuracy, end to end", pct(m.verdict.accuracy)],
            ["", "Accuracy, claims the extractor found", pct(m.verdict.accuracy_given_found)],
            ["Explanation", "No invented numbers (of model explanations)", pct(m.explanation.pass_rate)],
        ],
    )  # fmt: skip
    out += ["## Verdicts: expected (rows) against answered (columns)", ""]
    out += _confusion(m)
    out += _failures(report)
    out += ["## Cost", ""]
    c = m.cost
    out += [
        (
            f"- {c.model_calls} model calls ({c.failed_calls} failed), "
            f"{_num(c.calls_per_claim)} per claim; {c.prompt_tokens} prompt and "
            f"{c.completion_tokens} completion tokens."
        ),
        (
            f"- {c.seconds:.1f} s in all: {_num(c.seconds_per_claim)} s per claim; per text "
            f"median {_num(c.seconds_p50_per_text)} s, 95th percentile {_num(c.seconds_p95_per_text)} s."
        ),
        (
            f"- Source series: {c.series_requests} requests, {c.series_cache_hits} served from the "
            f"cache ({_rate(c.series_cache_hit_rate)}). The answer cache is not used in a run."
        ),
        "",
    ]
    out += _table(
        ["Step", "Provider", "Model", "Calls", "Failed", "Tokens", "Mean latency"],
        [
            [s.step, s.provider, s.model, str(s.calls), str(s.failed), str(s.tokens),
             f"{s.mean_latency_ms:.0f} ms"]
            for s in c.by_step_provider
        ],
    )  # fmt: skip
    return "\n".join(out)


def _providers(report: Report) -> str:
    if report.provider != ROUTER:
        return f"every step on {report.provider}"
    return (
        "each step's preference list ("
        + "; ".join(
            f"{step}: {', '.join(models[:1])}{' …' if len(models) > 1 else ''}"
            for step, models in report.steps.items()
            if step != "smoke"
        )
        + ")"
    )


def _excluded(m: Metrics) -> list[str]:
    e = m.excluded
    if not (e.claims_not_run or e.claims_verdict_unavailable):
        return []
    return [
        (
            f"> **{e.claims_not_run + e.claims_verdict_unavailable} of {m.labelled_claims} claims "
            f"are left out of the accuracy figures**: {e.claims_not_run} in {e.texts_not_run} text(s) "
            f"the router could not serve, {e.claims_verdict_unavailable} whose data source did not "
            "answer. An outage is not a wrong answer, but a run with many of them says little."
        ),
        "",
    ]


def _confusion(m: Metrics) -> list[str]:
    v = m.verdict
    rows = [
        [expected, *(str(v.confusion[expected][got]) for got in v.labels), pct(v.per_label[expected])]
        for expected in v.confusion
    ]  # fmt: skip
    return _table(["expected \\ answered", *v.labels, "right"], rows)


def _failures(report: Report) -> list[str]:
    wrong = [o for t in report.texts for o in t.outcomes if o.verdict_ok is False]
    if not wrong:
        return ["## Wrong verdicts", "", "None.", ""]
    out = ["## Wrong verdicts", ""]
    steps = report.metrics.failures
    out.append(
        "First step that went wrong: "
        + ", ".join(f"{step} {n}" for step, n in sorted(steps.items(), key=lambda s: -s[1]))
        + ".\n"
    )
    out += _table(
        ["Claim", "Expected", "Answered", "Broke at", "Why"],
        [[_name(o), str(o.expected), o.verdict or MISSED, o.failed_step or "", o.reason] for o in wrong],
    )  # fmt: skip
    return out


def _name(o: ClaimOutcome) -> str:
    return f"{o.text_id}#{o.index + 1}"


def _num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:g}"


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"
