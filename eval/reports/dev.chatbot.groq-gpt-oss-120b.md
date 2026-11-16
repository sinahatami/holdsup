# Chatbot baseline: dev.chatbot.groq-gpt-oss-120b

- Benchmark `claims.jsonl` (dev split) at eval 0.2.0: 106 texts, 106 labelled claims.
- One plain prompt per text, no tools and no web search; the same five labels. Models: groq-gpt-oss-120b/openai/gpt-oss-120b. Run 2026-11-16 00:31 UTC.

> **4 of 106 claims are left out of the accuracy figures**: 4 in 4 text(s) the router could not serve, 0 whose data source did not answer. An outage is not a wrong answer, but a run with many of them says little.

## Verdict

- Accuracy: 44.1% (45/102).

## Verdicts: expected (rows) against answered (columns)

| expected \ answered | supported | supported_framing_matters | not_supported | partly_supported | cant_check | missed | right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported | 23 | 0 | 14 | 0 | 2 | 0 | 59.0% (23/39) |
| supported_framing_matters | 8 | 0 | 3 | 1 | 7 | 0 | 0.0% (0/19) |
| not_supported | 5 | 0 | 20 | 0 | 3 | 0 | 71.4% (20/28) |
| partly_supported | 0 | 0 | 0 | 2 | 5 | 0 | 28.6% (2/7) |
| cant_check | 4 | 0 | 4 | 1 | 0 | 0 | 0.0% (0/9) |

## Wrong verdicts

| Claim | Expected | Answered |
| --- | --- | --- |
| e001#1 | supported | not_supported |
| e007#1 | supported | not_supported |
| e010#1 | supported | not_supported |
| e011#1 | supported | not_supported |
| e016#1 | not_supported | supported |
| e018#1 | not_supported | cant_check |
| e019#1 | not_supported | cant_check |
| e021#1 | partly_supported | cant_check |
| e022#1 | supported_framing_matters | cant_check |
| e023#1 | supported_framing_matters | partly_supported |
| e024#1 | supported_framing_matters | not_supported |
| e025#1 | supported_framing_matters | cant_check |
| e026#1 | supported_framing_matters | cant_check |
| e027#1 | supported_framing_matters | cant_check |
| e028#1 | cant_check | not_supported |
| e029#1 | cant_check | supported |
| e030#1 | cant_check | not_supported |
| e033#1 | supported | not_supported |
| e035#1 | supported | not_supported |
| e036#1 | supported | not_supported |
| e041#1 | supported | cant_check |
| e043#1 | not_supported | cant_check |
| e046#1 | not_supported | supported |
| e050#1 | partly_supported | cant_check |
| e052#1 | supported_framing_matters | supported |
| e053#1 | supported_framing_matters | not_supported |
| e056#1 | supported_framing_matters | supported |
| e059#1 | cant_check | partly_supported |
| e060#1 | cant_check | not_supported |
| e065#1 | supported | not_supported |
| e081#1 | partly_supported | cant_check |
| e083#1 | supported_framing_matters | cant_check |
| e084#1 | supported_framing_matters | supported |
| e086#1 | supported_framing_matters | cant_check |
| e087#1 | supported_framing_matters | supported |
| e089#1 | cant_check | supported |
| e090#1 | cant_check | not_supported |
| e091#1 | supported | not_supported |
| e101#1 | supported | not_supported |
| e103#1 | not_supported | supported |
| e110#1 | partly_supported | cant_check |
| e113#1 | supported_framing_matters | supported |
| e115#1 | supported_framing_matters | cant_check |
| e116#1 | supported_framing_matters | not_supported |
| e118#1 | cant_check | supported |
| e119#1 | cant_check | supported |
| e121#1 | supported | not_supported |
| e127#1 | supported | not_supported |
| e128#1 | supported | not_supported |
| e129#1 | supported | cant_check |
| e130#1 | supported | not_supported |
| e137#1 | not_supported | supported |
| e139#1 | not_supported | supported |
| e141#1 | partly_supported | cant_check |
| e142#1 | supported_framing_matters | supported |
| e143#1 | supported_framing_matters | supported |
| e144#1 | supported_framing_matters | supported |

## Cost

- 140 model calls (38 failed), 1.32 per claim; 44624 prompt and 22133 completion tokens.
- 310.3 s in all: 2.93 s per claim; per text median 0.93 s, 95th percentile 7.64 s.
- Daily limit reached: groq-gpt-oss-120b. The router moved on to the next choice for the rest of the run.

| Step | Provider | Model | Calls | Failed | Tokens | Mean latency |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | groq-gpt-oss-120b | openai/gpt-oss-120b | 140 | 38 | 66757 | 494 ms |
