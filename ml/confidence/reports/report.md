# Confidence model

How likely a verdict is to be right, from signals the check already has; below the threshold the result page says "can't check confidently" and why (P4.5).

## Data

- Dev-split evaluation reports (eval 0.2.0, catalog 0.8.0): `dev.json` (sha256 61258725e247), `conf-cerebras.cerebras-gpt-oss-120b.json` (sha256 3bd74f2d7a99).
- 178 claims with a verdict other than cant_check: 155 right, 23 wrong, in 65 groups.
- Not rows: cant_check (nothing to abstain from): 15; no signals (a report from before P4.5): 4; no verdict (not run, source down, or missed by extraction): 15.
- Missing signals (read as the training mean): rerank_probability 2, rerank_margin 2, boundary_distance 4.

## Cross-validation

5 folds, grouped by statistic and place (a claim's rows from several runs stay in one fold); fold sizes 36, 36, 36, 35, 35. Every figure is out of fold.

| Model | Brier | Log loss | AUC |
|---|---|---|---|
| Base rate (the training share right, for every claim) | 0.113 | 0.388 | n/a |
| Logistic regression, reranker margin only | 0.121 | 0.443 | 0.305 |
| Logistic regression, every signal (not served) | 0.117 | 0.474 | 0.465 |
| Gradient boosting, every signal | 0.114 | 0.407 | 0.605 |

- The logistic regression does not beat the base rate on the Brier score, so it is not exported: the API serves no confidence model and never abstains.
- Gradient boosting is not clearly better (a clear gain is a Brier score 0.01 lower).

## Calibration (logistic regression, out of fold)

| Probability | Claims | Mean probability | Share right |
|---|---|---|---|
| 0.0–0.2 | 3 | 0.025 | 33.3% |
| 0.2–0.4 | 0 | n/a | n/a |
| 0.4–0.6 | 0 | n/a | n/a |
| 0.6–0.8 | 6 | 0.735 | 100.0% |
| 0.8–1.0 | 169 | 0.900 | 87.6% |

## Accuracy against coverage (logistic regression, out of fold)

| Answer at most | Answered | Accuracy | Lowest probability answered |
|---|---|---|---|
| 100% | 178 (100.0%) | 87.1% | 0.000 |
| 90% | 159 (89.3%) | 86.8% | 0.831 |
| 80% | 142 (79.8%) | 86.6% | 0.854 |
| 70% | 124 (69.7%) | 85.5% | 0.874 |
| 60% | 106 (59.6%) | 87.7% | 0.884 |
| 50% | 89 (50.0%) | 86.5% | 0.897 |

## Threshold

- Target: answered verdicts right 90.0% of the time (cannot reach; the most accurate coverage is used).
- Threshold 0.915: answers 67 of 178 (37.6%), abstains on 62.4%; answered accuracy 89.6% out of fold.
- Confidence is high at 0.92 or above, medium from the threshold up, low (abstain) below it.

## Logistic regression coefficients (per standard deviation; trained on every row)

| Signal | Weight | Expected | As expected |
|---|---|---|---|
| rerank_probability | +0.239 | + | yes |
| rerank_margin | +0.058 | + | yes |
| definition_mismatch | -0.567 | − | yes |
| data_age_years | +0.321 | − | no: never a reason |
| series_length | +0.218 | + | yes |
| boundary_distance | +0.000 | + | yes |
| fallback_steps | -0.159 | − | yes |

Intercept +2.013.

## Limitations

- The served reranker was fine-tuned on every dev claim (P4.3), so on these rows its probabilities and margins are in-sample: higher, and more often right, than on claims it has never seen. The model may lean on them more than it should; the held-out evaluation (P4.7) is the honest check of its calibration.
- Few rows, most of them right, and many are one claim in two runs: one claim moves the figures by about a point, and the threshold can move with them.
- Rows come from the runs named above; a run on backup models (a provider at its daily limit) has more wrong verdicts and more fallback steps than a usual day.
