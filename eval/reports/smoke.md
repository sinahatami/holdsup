# Evaluation: smoke

- Benchmark `smoke_claims.jsonl` (dev split) at eval 0.2.0: 10 texts, 14 labelled claims, 12 extracted.
- App 0.0.0, catalog 0.8.0, tolerances v5.
- Providers: each step's preference list (extract: groq-gpt-oss-20b/openai/gpt-oss-20b …; match: groq-gpt-oss-120b/openai/gpt-oss-120b …; plan: groq-gpt-oss-120b/openai/gpt-oss-120b …; explain: groq-gpt-oss-20b/openai/gpt-oss-20b …). Run 2026-11-13 00:08 UTC.

> **1 of 14 claims are left out of the accuracy figures**: 0 in 0 text(s) the router could not serve, 1 whose data source did not answer. An outage is not a wrong answer, but a run with many of them says little.

## Per step

| Step | Metric | Result |
| --- | --- | --- |
| Extraction | Precision (extracted claims that are labelled) | 100.0% (12/12) |
|  | Recall (labelled claims found) | 85.7% (12/14) |
|  | Place right | 100.0% (12/12) |
|  | Start right | 83.3% (10/12) |
|  | End right | 91.7% (11/12) |
| Matching | Top-1 (the labelled statistic picked) | 91.7% (11/12) |
|  | Recall@8 of the search alone | 100.0% (12/12) |
| Verdict | Accuracy, end to end | 84.6% (11/13) |
|  | Accuracy, claims the extractor found | 100.0% (11/11) |
| Explanation | No invented numbers (of model explanations) | 81.8% (9/11) |

## Verdicts: expected (rows) against answered (columns)

| expected \ answered | supported | supported_framing_matters | not_supported | partly_supported | cant_check | missed | right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported | 5 | 0 | 0 | 0 | 0 | 1 | 83.3% (5/6) |
| supported_framing_matters | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| not_supported | 0 | 0 | 6 | 0 | 0 | 0 | 100.0% (6/6) |
| partly_supported | 0 | 0 | 0 | 0 | 0 | 1 | 0.0% (0/1) |
| cant_check | 0 | 0 | 0 | 0 | 0 | 0 | n/a |

## Wrong verdicts

First step that went wrong: extract 2.

| Claim | Expected | Answered | Broke at | Why |
| --- | --- | --- | --- | --- |
| c001#2 | partly_supported | missed | extract |  |
| c007#2 | supported | missed | extract |  |

## Cost

- 78 model calls (21 failed), 5.57 per claim; 62400 prompt and 35983 completion tokens.
- 198.8 s in all: 14.2 s per claim; per text median 12.71 s, 95th percentile 69.68 s.
- Source series: 13 requests, 5 served from the cache (38%). The answer cache is not used in a run.

| Step | Provider | Model | Calls | Failed | Tokens | Mean latency |
| --- | --- | --- | --- | --- | --- | --- |
| explain | groq-gpt-oss-120b | openai/gpt-oss-120b | 2 | 1 | 815 | 383 ms |
| explain | groq-gpt-oss-20b | openai/gpt-oss-20b | 14 | 2 | 12625 | 596 ms |
| explain | mistral-ministral-14b | ministral-14b-2512 | 2 | 1 | 968 | 854 ms |
| explain | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 1 | 0 | 1602 | 7980 ms |
| extract | groq-gpt-oss-120b | openai/gpt-oss-120b | 4 | 3 | 2774 | 486 ms |
| extract | groq-gpt-oss-20b | openai/gpt-oss-20b | 9 | 4 | 16057 | 896 ms |
| extract | mistral-ministral-14b | ministral-14b-2512 | 2 | 1 | 1160 | 1396 ms |
| extract | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 3 | 0 | 5789 | 6835 ms |
| match | groq-gpt-oss-120b | openai/gpt-oss-120b | 14 | 4 | 13001 | 646 ms |
| match | mistral-ministral-14b | ministral-14b-2512 | 2 | 0 | 2483 | 1531 ms |
| match | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 6 | 0 | 9788 | 3941 ms |
| plan | groq-gpt-oss-120b | openai/gpt-oss-120b | 12 | 4 | 13986 | 806 ms |
| plan | mistral-ministral-14b | ministral-14b-2512 | 3 | 1 | 1587 | 1298 ms |
| plan | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 4 | 0 | 15748 | 23656 ms |
