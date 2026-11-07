# eval/

Benchmark claims, splits, the evaluation runner, and reports. The benchmark has its own version in `VERSION`.

## Smoke set

`smoke_claims.jsonl` is the start of the 30-claim smoke set that `make eval-smoke` (P4.2) runs on every PR touching `apps/api` or `ml/`. One JSON object per line: `id`, `text`, `source_url`, `added`, `why` (for regressions), and `claims`, each with `quote`, `indicator` (catalog id), `geo`, `window` (`[start, end]`; `latest` for the present), `expected` (a verdict label) and `justification` (the numbers behind it). A claim that once came out wrong goes in here with the fix, and stays, so it cannot quietly break again. Expected labels that depend on "today" change when the source publishes new data; the justification names the period and the source's update date.
