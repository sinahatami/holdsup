# Evaluation: smoke

- Benchmark `smoke_claims.jsonl` (dev split) at eval 0.1.0: 10 texts, 14 labelled claims, 12 extracted.
- App 0.0.0, catalog 0.8.0, tolerances v5.
- Providers: each step's preference list (extract: groq-gpt-oss-20b/openai/gpt-oss-20b …; match: groq-gpt-oss-120b/openai/gpt-oss-120b …; plan: groq-gpt-oss-120b/openai/gpt-oss-120b …; explain: groq-gpt-oss-20b/openai/gpt-oss-20b …). Run 2026-11-12 22:53 UTC.

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
| Verdict | Accuracy, end to end | 85.7% (12/14) |
|  | Accuracy, claims the extractor found | 100.0% (12/12) |
| Explanation | No invented numbers (of model explanations) | 83.3% (10/12) |

## Verdicts: expected (rows) against answered (columns)

| expected \ answered | supported | supported_framing_matters | not_supported | partly_supported | cant_check | missed | right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported | 6 | 0 | 0 | 0 | 0 | 1 | 85.7% (6/7) |
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

- 83 model calls (24 failed), 5.93 per claim; 62548 prompt and 38932 completion tokens.
- 222.3 s in all: 15.88 s per claim; per text median 14.69 s, 95th percentile 54.15 s.
- Source series: 13 requests, 5 served from the cache (38%). The answer cache is not used in a run.

| Step | Provider | Model | Calls | Failed | Tokens | Mean latency |
| --- | --- | --- | --- | --- | --- | --- |
| explain | groq-gpt-oss-120b | openai/gpt-oss-120b | 2 | 1 | 894 | 479 ms |
| explain | groq-gpt-oss-20b | openai/gpt-oss-20b | 14 | 3 | 12631 | 633 ms |
| explain | mistral-ministral-14b | ministral-14b-2512 | 5 | 3 | 1189 | 519 ms |
| explain | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 3 | 0 | 4106 | 5485 ms |
| extract | groq-gpt-oss-120b | openai/gpt-oss-120b | 4 | 4 | 0 | 70 ms |
| extract | groq-gpt-oss-20b | openai/gpt-oss-20b | 9 | 5 | 13024 | 1140 ms |
| extract | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 6 | 0 | 14394 | 9796 ms |
| match | groq-gpt-oss-120b | openai/gpt-oss-120b | 13 | 2 | 14667 | 752 ms |
| match | mistral-ministral-14b | ministral-14b-2512 | 1 | 1 | 0 | 132 ms |
| match | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 6 | 0 | 10058 | 4781 ms |
| plan | groq-gpt-oss-120b | openai/gpt-oss-120b | 15 | 5 | 18165 | 844 ms |
| plan | mistral-ministral-14b | ministral-14b-2512 | 2 | 0 | 1464 | 897 ms |
| plan | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 3 | 0 | 10888 | 22318 ms |
