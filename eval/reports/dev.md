# Evaluation: dev

- Benchmark `claims.jsonl` (dev split) at eval 0.2.0: 106 texts, 106 labelled claims, 105 extracted.
- App 0.0.0, catalog 0.8.0, tolerances v5.
- Providers: each step's preference list (extract: groq-gpt-oss-20b/openai/gpt-oss-20b …; match: groq-gpt-oss-120b/openai/gpt-oss-120b …; plan: groq-gpt-oss-120b/openai/gpt-oss-120b …; explain: groq-gpt-oss-20b/openai/gpt-oss-20b …; baseline: groq-gpt-oss-120b/openai/gpt-oss-120b …). Run 2026-11-17 22:03 UTC.

> **14 of 106 claims are left out of the accuracy figures**: 0 in 0 text(s) the router could not serve, 14 whose data source did not answer. An outage is not a wrong answer, but a run with many of them says little.

## Per step

| Step | Metric | Result |
| --- | --- | --- |
| Extraction | Precision (extracted claims that are labelled) | 100.0% (105/105) |
|  | Recall (labelled claims found) | 99.1% (105/106) |
|  | Place right | 100.0% (105/105) |
|  | Start right | 99.1% (104/105) |
|  | End right | 99.1% (104/105) |
| Matching | Top-1 (the labelled statistic picked) | 99.1% (104/105) |
|  | Recall@8 of the search alone | 99.0% (102/103) |
| Verdict | Accuracy, end to end | 82.6% (76/92) |
|  | Accuracy, claims the extractor found | 83.5% (76/91) |
| Explanation | No invented numbers (of model explanations) | 100.0% (81/81) |

## Verdicts: expected (rows) against answered (columns)

| expected \ answered | supported | supported_framing_matters | not_supported | partly_supported | cant_check | missed | right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported | 30 | 2 | 0 | 0 | 0 | 0 | 93.8% (30/32) |
| supported_framing_matters | 8 | 7 | 4 | 0 | 0 | 0 | 36.8% (7/19) |
| not_supported | 0 | 0 | 26 | 0 | 0 | 0 | 100.0% (26/26) |
| partly_supported | 1 | 0 | 0 | 4 | 0 | 0 | 80.0% (4/5) |
| cant_check | 0 | 0 | 0 | 0 | 9 | 1 | 90.0% (9/10) |

## Wrong verdicts

First step that went wrong: verdict 14, extract 1, match 1.

| Claim | Expected | Answered | Broke at | Why |
| --- | --- | --- | --- | --- |
| e022#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e023#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e024#1 | supported_framing_matters | not_supported | verdict | Outside tolerance for the stated window. |
| e026#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e027#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e028#1 | cant_check | missed | extract |  |
| e050#1 | partly_supported | supported | verdict | Holds within tolerance. |
| e083#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e084#1 | supported_framing_matters | not_supported | verdict | Outside tolerance for the stated window. |
| e086#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e113#1 | supported_framing_matters | not_supported | match | Outside tolerance for the stated window. |
| e115#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |
| e116#1 | supported_framing_matters | not_supported | verdict | Outside tolerance for the stated window. |
| e124#1 | supported | supported_framing_matters | verdict | Holds within tolerance, but the claim is per person; the figures are a total (current international $). |
| e125#1 | supported | supported_framing_matters | verdict | Holds within tolerance, but the claim is per person; the figures are a total (current international $). |
| e146#1 | supported_framing_matters | supported | verdict | Holds within tolerance. |

## Cost

- 450 model calls (123 failed), 4.25 per claim; 440441 prompt and 139098 completion tokens.
- 2779.5 s in all: 26.22 s per claim; per text median 11.74 s, 95th percentile 93.17 s.
- Source series: 137 requests, 56 served from the cache (41%). The answer cache is not used in a run.
- Daily limit reached: groq-gpt-oss-120b, groq-gpt-oss-20b, openrouter-nemotron-free. The router moved on to the next choice for the rest of the run.

| Step | Provider | Model | Calls | Failed | Tokens | Mean latency |
| --- | --- | --- | --- | --- | --- | --- |
| explain | cerebras-gpt-oss-120b | gpt-oss-120b | 23 | 4 | 16859 | 384 ms |
| explain | groq-gpt-oss-120b | openai/gpt-oss-120b | 12 | 2 | 8835 | 691 ms |
| explain | groq-gpt-oss-20b | openai/gpt-oss-20b | 46 | 6 | 37849 | 618 ms |
| explain | mistral-ministral-14b | ministral-14b-2512 | 24 | 4 | 11382 | 888 ms |
| explain | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 1 | 1 | 0 | 56 ms |
| extract | cerebras-gpt-oss-120b | gpt-oss-120b | 47 | 2 | 143224 | 657 ms |
| extract | groq-gpt-oss-120b | openai/gpt-oss-120b | 30 | 20 | 27323 | 562 ms |
| extract | groq-gpt-oss-20b | openai/gpt-oss-20b | 60 | 28 | 95471 | 757 ms |
| extract | mistral-ministral-14b | ministral-14b-2512 | 28 | 12 | 17724 | 1374 ms |
| extract | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 5 | 1 | 10274 | 10006 ms |
| match | cerebras-gpt-oss-120b | gpt-oss-120b | 11 | 1 | 15834 | 426 ms |
| match | groq-gpt-oss-120b | openai/gpt-oss-120b | 33 | 18 | 21502 | 473 ms |
| match | mistral-ministral-14b | ministral-14b-2512 | 8 | 2 | 8999 | 643 ms |
| match | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 5 | 0 | 9538 | 2748 ms |
| plan | cerebras-gpt-oss-120b | gpt-oss-120b | 30 | 4 | 48337 | 540 ms |
| plan | groq-gpt-oss-120b | openai/gpt-oss-120b | 70 | 14 | 94129 | 914 ms |
| plan | mistral-ministral-14b | ministral-14b-2512 | 13 | 4 | 6916 | 1206 ms |
| plan | openrouter-nemotron-free | nvidia/nemotron-3.5-super-vl:free | 4 | 0 | 5343 | 5610 ms |
