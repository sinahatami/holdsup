# Chatbot baseline: test.chatbot.groq-gpt-oss-120b

- Benchmark `claims.jsonl` (test split) at eval 0.2.0: 44 texts, 44 labelled claims.
- One plain prompt per text, no tools and no web search; the same five labels. Models: groq-gpt-oss-120b/openai/gpt-oss-120b. Run 2026-11-19 09:13 UTC.

## Verdict

- Accuracy: 38.6% (17/44).

## Verdicts: expected (rows) against answered (columns)

| expected \ answered | supported | supported_framing_matters | not_supported | partly_supported | cant_check | missed | right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported | 8 | 0 | 7 | 1 | 0 | 0 | 50.0% (8/16) |
| supported_framing_matters | 2 | 1 | 1 | 1 | 4 | 0 | 11.1% (1/9) |
| not_supported | 3 | 0 | 7 | 0 | 2 | 0 | 58.3% (7/12) |
| partly_supported | 0 | 0 | 2 | 0 | 1 | 0 | 0.0% (0/3) |
| cant_check | 0 | 0 | 3 | 0 | 1 | 0 | 25.0% (1/4) |

## Wrong verdicts

| Claim | Expected | Answered |
| --- | --- | --- |
| e004#1 | supported | not_supported |
| e038#1 | supported | not_supported |
| e048#1 | not_supported | cant_check |
| e051#1 | partly_supported | cant_check |
| e054#1 | supported_framing_matters | supported |
| e055#1 | supported_framing_matters | partly_supported |
| e057#1 | supported_framing_matters | cant_check |
| e058#1 | cant_check | not_supported |
| e061#1 | supported | not_supported |
| e062#1 | supported | not_supported |
| e064#1 | supported | not_supported |
| e068#1 | supported | partly_supported |
| e069#1 | supported | not_supported |
| e074#1 | not_supported | supported |
| e079#1 | not_supported | cant_check |
| e080#1 | partly_supported | not_supported |
| e082#1 | supported_framing_matters | not_supported |
| e085#1 | supported_framing_matters | cant_check |
| e088#1 | cant_check | not_supported |
| e106#1 | not_supported | supported |
| e111#1 | partly_supported | not_supported |
| e112#1 | supported_framing_matters | cant_check |
| e114#1 | supported_framing_matters | cant_check |
| e117#1 | supported_framing_matters | supported |
| e123#1 | supported | not_supported |
| e138#1 | not_supported | supported |
| e148#1 | cant_check | not_supported |

## Cost

- 70 model calls (26 failed), 1.59 per claim; 19263 prompt and 9461 completion tokens.
- 156.7 s in all: 3.56 s per claim; per text median 3.81 s, 95th percentile 7.03 s.

| Step | Provider | Model | Calls | Failed | Tokens | Mean latency |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | groq-gpt-oss-120b | openai/gpt-oss-120b | 70 | 26 | 28724 | 515 ms |
