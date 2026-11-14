# eval/

Benchmark claims, splits, the evaluation runner, and reports. The benchmark has its own version in `VERSION`.

## Smoke set

`smoke_claims.jsonl` is the start of the 30-claim smoke set that `make eval-smoke` runs on every PR touching `apps/api`, `ml/`, `eval/` or the catalog, and every night. One JSON object per line: `id`, `text`, `source_url`, `added`, `why` (for regressions), an optional `split` (`dev` or `test`; no split counts as dev), and `claims`, each with `quote`, `indicator` (catalog id, or `null` when the catalog has nothing for it), `geo`, `window` (`[start, end]`; `latest` for the present), `expected` (a verdict label) and `justification` (the numbers behind it). A claim that once came out wrong goes in here with the fix, and stays, so it cannot quietly break again. Expected labels that depend on "today" change when the source publishes new data; the justification names the period and the source's update date.

The runner validates the file strictly (unknown keys, bad periods, unknown labels, duplicate ids, indicators missing from the catalog) and reports every problem at once, so a typo cannot pass as a model failure.

## The runner

Code: `apps/api/scripts/evaluation/` (offline tooling, never imported by a request path). It runs each text through the real pipeline, one at a time and without the answer cache, and scores every step.

```bash
make eval-smoke      # smoke claims; fails on a verdict-accuracy drop of more than 5 points vs baseline.json
make eval-baseline   # the same run, accepted as the new baseline.json (read the report first)
make eval            # the dev split of claims.jsonl (P4.1); manual
make eval ARGS="--provider groq-gpt-oss-120b"   # every step forced onto one provider
make eval ARGS=--resume   # continue a run that stopped part-way; see below
```

A run keeps every text it has finished in `reports/<name>.partial.jsonl` (ignored by git) until the report is written. The dev split is more model calls than one day of the free quota, and a run that long can be stopped (out of memory, a restart), so `--resume` keeps those texts and runs the rest, including any the router could not serve, and the report covers every text. It resumes only a partial run of the same benchmark, split, provider and versions; without `--resume` a run starts over. Locally the app version carries no commit, so do not change the code between the runs you resume.

Reports land in `reports/<name>.json` (what the `/eval` page reads) and `reports/<name>.md`, stamped with the app, catalog, tolerances and eval versions and the provider and model behind each step. They hold ids, the labelled quotes, verdicts and code-written reasons, never raw model output or the benchmark's full texts.

How the steps are scored. Each step counts only the claims that reached it; the verdict also has an end-to-end figure.

| Step | Figure |
| --- | --- |
| Extraction | Precision and recall of extracted claims against labelled ones (paired one to one by quote overlap), and place, start and end right |
| Matching | Top-1 (the labelled statistic, or none when none is labelled) and recall@8 of the catalog search alone |
| Verdict | Accuracy end to end (a claim the extractor missed is wrong) and given extraction; confusion matrix over the five labels plus `missed`; each wrong verdict is traced to the first step that broke |
| Explanation | Share of model explanations whose numbers were all in the computed results |
| Cost | Model calls, tokens and seconds per claim and per text, by step and provider; source-series cache hits |

A text the router cannot serve, and a claim whose data source is down, leave the accuracy figures but are counted and shown: an outage is not a wrong answer. The gate refuses to judge (exit 3) when more than 20% of the claims dropped out, when there is no baseline, or when the baseline is for another benchmark version; bump `VERSION`, then `make eval-baseline`. With a small set one claim is worth several points, so read the report before blaming a change.

The test split is held out: `--split test` and `--split all` are refused without `--final` (P4.7). Tuning uses dev only.
