# eval/

Benchmark claims, splits, the evaluation runner, and reports. The benchmark has its own version in `VERSION`.

## Smoke set

`smoke_claims.jsonl` is the start of the 30-claim smoke set that `make eval-smoke` runs on every PR that can change a verdict (the API's code, the evaluation scripts, this file, `baseline.json`, `VERSION`, the catalog or the dependencies), and every night. One JSON object per line: `id`, `text`, `source_url`, `added`, `why` (for regressions), an optional `split` (`dev` or `test`; no split counts as dev), and `claims`, each with `quote`, `indicator` (catalog id, or `null` when the catalog has nothing for it), `geo`, `window` (`[start, end]`; `latest` for the present), `expected` (a verdict label) and `justification` (the numbers behind it). A claim that once came out wrong goes in here with the fix, and stays, so it cannot quietly break again. Expected labels that depend on "today" change when the source publishes new data; the justification names the period and the source's update date.

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

A text the router cannot serve, and a claim whose data source is down, leave the accuracy figures but are counted and shown: an outage is not a wrong answer. The gate refuses to judge (exit 3) when more than 20% of the claims dropped out, when there is no baseline, or when the baseline is for another benchmark version (bump `VERSION`, then `make eval-baseline`), and when a rate limit sent a step's first-choice model to a fallback that answered (the baseline measures the first choices). With a small set one claim is worth several points, so read the report before blaming a change.

`--replay DIR` answers each model request that has a saved reply in `DIR` from it and asks the providers only for the rest (a changed prompt, another model, new data in a plan prompt), saving what they say; `--record DIR` asks everything afresh and saves it. In CI the nightly run records into the Actions cache and pull requests replay from it, so a PR that changes no prompt spends no free-tier quota, and its gate measures the code rather than the models' day-to-day variation. Locally: `make eval-smoke ARGS="--replay .cache/eval-replies"`.

## The chatbot baseline (P4.6)

```bash
make eval-chatbot                                   # the dev split -> reports/dev.chatbot.{json,md}
make eval-chatbot ARGS="--provider gemini-flash"    # one model -> reports/dev.chatbot.gemini-flash.json
make eval-chatbot ARGS=--resume                     # continue a stopped run
make eval-chatbot ARGS="--provider mistral-ministral-14b --resume --wait-budget 9000"
```

A run waits out rate limits for ten minutes in all, then leaves the texts it could not serve as "not run" (`--wait-budget SECONDS`). A provider held to about a call a minute, such as Mistral's Experiment plan, needs about two hours for the 106 dev texts, so give it a budget of that size and run it from a restartable unit with `--resume`.

A general chatbot gets the text and the labelled claims in one plain question ("is each claim true?", the five labels with a line each) and answers from what it knows: no tools, no data, no web search. Its answers are scored against the same labels, with the same confusion matrix and cost figures, as a report of `kind: chatbot` (verdicts and cost only: it has no extraction, matching or explanation). The router step is `baseline` in `providers.yaml`; the run allows the offline-only provider (`--use offline`). A claim it gives no answer for counts as wrong ("no answer"); a text no provider could serve is left out and counted.

`GET /v1/eval` joins `<split>.json` with the split's chatbot run (the one that answered the most claims, whether `<split>.chatbot.json` or one provider's `<split>.chatbot.<provider>.json`) on the claims both could be scored on, and the `/eval` page shows the result, with the claims HoldsUp loses and the first step that broke in each.

The test split is held out: `--split test` and `--split all` are refused without `--final` (P4.7). Tuning uses dev only.
