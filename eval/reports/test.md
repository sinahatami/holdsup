# Evaluation: test

- Benchmark `claims.jsonl` (test split) at eval 0.2.0: 44 texts, 44 labelled claims, 44 extracted.
- App 0.0.0, catalog 0.8.0, tolerances v6.
- Providers: each step's preference list (extract: groq-gpt-oss-20b/openai/gpt-oss-20b …; match: groq-gpt-oss-120b/openai/gpt-oss-120b …; plan: groq-gpt-oss-120b/openai/gpt-oss-120b …; explain: groq-gpt-oss-20b/openai/gpt-oss-20b …; baseline: groq-gpt-oss-120b/openai/gpt-oss-120b …). Run 2026-11-18 12:54 UTC.

## Per step

| Step | Metric | Result |
| --- | --- | --- |
| Extraction | Precision (extracted claims that are labelled) | 100.0% (44/44) |
|  | Recall (labelled claims found) | 100.0% (44/44) |
|  | Place right | 100.0% (44/44) |
|  | Start right | 97.7% (43/44) |
|  | End right | 100.0% (44/44) |
| Matching | Top-1 (the labelled statistic picked) | 97.7% (43/44) |
|  | Recall@8 of the search alone | 100.0% (43/43) |
| Verdict | Accuracy, end to end | 88.6% (39/44) |
|  | Accuracy, claims the extractor found | 88.6% (39/44) |
| Explanation | No invented numbers (of model explanations) | 100.0% (40/40) |

## Verdicts: expected (rows) against answered (columns)

| expected \ answered | supported | supported_framing_matters | not_supported | partly_supported | cant_check | missed | right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported | 16 | 0 | 0 | 0 | 0 | 0 | 100.0% (16/16) |
| supported_framing_matters | 2 | 6 | 0 | 0 | 1 | 0 | 66.7% (6/9) |
| not_supported | 0 | 0 | 12 | 0 | 0 | 0 | 100.0% (12/12) |
| partly_supported | 1 | 0 | 0 | 2 | 0 | 0 | 66.7% (2/3) |
| cant_check | 0 | 0 | 1 | 0 | 3 | 0 | 75.0% (3/4) |

## Wrong verdicts

First step that went wrong: verdict 4, match 1.

| Claim | Expected | Answered | Broke at | Why |
| --- | --- | --- | --- | --- |
| e057#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e085#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e111#1 | partly_supported | supported | verdict | Holds within tolerance. |
| e112#1 | supported_framing_matters | cant_check | match | HoldsUp doesn't have a statistic that matches this claim yet. |
| e148#1 | cant_check | not_supported | verdict | Outside tolerance for the stated window. |

## Cost

- 224 model calls (70 failed), 5.09 per claim; 198164 prompt and 56130 completion tokens.
- 819.3 s in all: 18.62 s per claim; per text median 11.78 s, 95th percentile 59.17 s.
- Source series: 61 requests, 23 served from the cache (38%). The answer cache is not used in a run.
- Daily limit reached: groq-gpt-oss-120b, groq-gpt-oss-20b, openrouter-nemotron-free. The router moved on to the next choice for the rest of the run.

| Step | Provider | Model | Calls | Failed | Tokens | Mean latency |
| --- | --- | --- | --- | --- | --- | --- |
| explain | cerebras-gpt-oss-120b | gpt-oss-120b | 10 | 1 | 8483 | 407 ms |
| explain | groq-gpt-oss-120b | openai/gpt-oss-120b | 5 | 1 | 3050 | 611 ms |
| explain | groq-gpt-oss-20b | openai/gpt-oss-20b | 24 | 3 | 21050 | 850 ms |
| explain | mistral-ministral-14b | ministral-14b-2512 | 8 | 2 | 3224 | 699 ms |
| extract | cerebras-gpt-oss-120b | gpt-oss-120b | 14 | 1 | 41671 | 694 ms |
| extract | groq-gpt-oss-120b | openai/gpt-oss-120b | 19 | 14 | 13626 | 426 ms |
| extract | groq-gpt-oss-20b | openai/gpt-oss-20b | 31 | 15 | 45910 | 662 ms |
| extract | mistral-ministral-14b | ministral-14b-2512 | 15 | 5 | 11202 | 1392 ms |
| extract | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 1 | 1 | 0 | 235 ms |
| match | cerebras-gpt-oss-120b | gpt-oss-120b | 9 | 0 | 13870 | 405 ms |
| match | groq-gpt-oss-120b | openai/gpt-oss-120b | 26 | 11 | 18422 | 530 ms |
| match | mistral-ministral-14b | ministral-14b-2512 | 4 | 1 | 6266 | 604 ms |
| plan | cerebras-gpt-oss-120b | gpt-oss-120b | 13 | 2 | 21083 | 550 ms |
| plan | groq-gpt-oss-120b | openai/gpt-oss-120b | 35 | 10 | 40566 | 737 ms |
| plan | mistral-ministral-14b | ministral-14b-2512 | 10 | 3 | 5871 | 1152 ms |
