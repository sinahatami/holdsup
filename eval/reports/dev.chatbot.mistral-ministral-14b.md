# Chatbot baseline: dev.chatbot.mistral-ministral-14b

- Benchmark `claims.jsonl` (dev split) at eval 0.2.0: 106 texts, 106 labelled claims.
- One plain prompt per text, no tools and no web search; the same five labels. Models: mistral-ministral-14b/ministral-14b-2512. Run 2026-11-15 19:49 UTC.

## Verdict

- Accuracy: 43.4% (46/106).

## Verdicts: expected (rows) against answered (columns)

| expected \ answered | supported | supported_framing_matters | not_supported | partly_supported | cant_check | missed | right |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supported | 33 | 3 | 1 | 0 | 2 | 0 | 84.6% (33/39) |
| supported_framing_matters | 7 | 7 | 2 | 0 | 5 | 0 | 33.3% (7/21) |
| not_supported | 14 | 5 | 3 | 0 | 6 | 0 | 10.7% (3/28) |
| partly_supported | 1 | 2 | 1 | 0 | 3 | 0 | 0.0% (0/7) |
| cant_check | 5 | 2 | 1 | 0 | 3 | 0 | 27.3% (3/11) |

## Wrong verdicts

| Claim | Expected | Answered |
| --- | --- | --- |
| e001#1 | supported | supported_framing_matters |
| e011#1 | supported | cant_check |
| e012#1 | not_supported | supported |
| e014#1 | not_supported | cant_check |
| e016#1 | not_supported | supported |
| e017#1 | not_supported | cant_check |
| e018#1 | not_supported | cant_check |
| e019#1 | not_supported | cant_check |
| e020#1 | partly_supported | supported |
| e021#1 | partly_supported | not_supported |
| e022#1 | supported_framing_matters | not_supported |
| e023#1 | supported_framing_matters | supported |
| e025#1 | supported_framing_matters | supported |
| e026#1 | supported_framing_matters | cant_check |
| e028#1 | cant_check | supported |
| e029#1 | cant_check | supported |
| e030#1 | cant_check | not_supported |
| e031#1 | supported | not_supported |
| e035#1 | supported | supported_framing_matters |
| e040#1 | supported | supported_framing_matters |
| e041#1 | supported | cant_check |
| e043#1 | not_supported | cant_check |
| e044#1 | not_supported | supported_framing_matters |
| e045#1 | not_supported | supported |
| e046#1 | not_supported | supported |
| e050#1 | partly_supported | supported_framing_matters |
| e052#1 | supported_framing_matters | cant_check |
| e056#1 | supported_framing_matters | supported |
| e059#1 | cant_check | supported |
| e060#1 | cant_check | supported_framing_matters |
| e072#1 | not_supported | supported_framing_matters |
| e075#1 | not_supported | cant_check |
| e076#1 | not_supported | supported |
| e077#1 | not_supported | supported |
| e081#1 | partly_supported | cant_check |
| e083#1 | supported_framing_matters | cant_check |
| e086#1 | supported_framing_matters | not_supported |
| e087#1 | supported_framing_matters | supported |
| e089#1 | cant_check | supported |
| e102#1 | not_supported | supported |
| e103#1 | not_supported | supported |
| e105#1 | not_supported | supported |
| e107#1 | not_supported | supported |
| e108#1 | not_supported | supported |
| e109#1 | not_supported | supported_framing_matters |
| e110#1 | partly_supported | supported_framing_matters |
| e113#1 | supported_framing_matters | cant_check |
| e116#1 | supported_framing_matters | cant_check |
| e118#1 | cant_check | supported |
| e119#1 | cant_check | supported_framing_matters |
| e134#1 | not_supported | supported |
| e135#1 | not_supported | supported_framing_matters |
| e136#1 | not_supported | supported_framing_matters |
| e137#1 | not_supported | supported |
| e139#1 | not_supported | supported |
| e140#1 | partly_supported | cant_check |
| e141#1 | partly_supported | cant_check |
| e142#1 | supported_framing_matters | supported |
| e145#1 | supported_framing_matters | supported |
| e146#1 | supported_framing_matters | supported |

## Cost

- 165 model calls (59 failed), 1.56 per claim; 19729 prompt and 3277 completion tokens.
- 3771.8 s in all: 35.58 s per claim; per text median 62.28 s, 95th percentile 63.35 s.

| Step | Provider | Model | Calls | Failed | Tokens | Mean latency |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | mistral-ministral-14b | ministral-14b-2512 | 165 | 59 | 23006 | 540 ms |
