# Confidence model

How likely a verdict is to be right, from signals the check already has; below the threshold the result page says "can't check confidently" and why (P4.5).

## Data

- Dev-split evaluation reports (eval 0.2.0, catalog 0.8.0): `dev.json` (sha256 2966ceeac3dd).
- 80 claims with a verdict other than cant_check: 67 right, 13 wrong, in 55 groups.
- Not rows: cant_check (nothing to abstain from): 9; no signals (a report from before P4.5): 1; no verdict (not run, source down, or missed by extraction): 16.
- Missing signals (read as the training mean): rerank_probability 1, rerank_margin 1, boundary_distance 1.

## Cross-validation

5 folds, grouped by statistic and place (a claim's rows from several runs stay in one fold); fold sizes 16, 16, 16, 16, 16. Every figure is out of fold.

| Model | Brier | Log loss | AUC |
|---|---|---|---|
| Base rate (the training share right, for every claim) | 0.138 | 0.452 | n/a |
| Logistic regression, reranker margin only | 0.135 | 0.445 | 0.478 |
| Logistic regression, every signal (served) | 0.139 | 0.454 | 0.561 |
| Gradient boosting, every signal | 0.122 | 0.417 | 0.715 |

- The served model does not beat the base rate on the Brier score, so it is not exported: the API serves no confidence model and never abstains.
- Gradient boosting is clearly better (serve it instead: P4.7) (a clear gain is a Brier score 0.01 lower).

## Calibration (served model, out of fold)

| Probability | Claims | Mean probability | Share right |
|---|---|---|---|
| 0.0–0.2 | 1 | 0.000 | 0.0% |
| 0.2–0.4 | 0 | n/a | n/a |
| 0.4–0.6 | 3 | 0.524 | 100.0% |
| 0.6–0.8 | 15 | 0.721 | 86.7% |
| 0.8–1.0 | 61 | 0.896 | 83.6% |

## Accuracy against coverage (served model, out of fold)

| Answer at most | Answered | Accuracy | Lowest probability answered |
|---|---|---|---|
| 100% | 80 (100.0%) | 83.8% | 0.000 |
| 90% | 72 (90.0%) | 84.7% | 0.667 |
| 80% | 64 (80.0%) | 84.4% | 0.789 |
| 70% | 56 (70.0%) | 83.9% | 0.824 |
| 60% | 48 (60.0%) | 85.4% | 0.852 |
| 50% | 40 (50.0%) | 87.5% | 0.878 |

## Threshold

- Target: answered verdicts right 90.0% of the time (reaches).
- Threshold 0.922: answers 20 of 80 (25.0%), abstains on 75.0%; answered accuracy 90.0% out of fold.
- Confidence is high at 0.92 or above, medium from the threshold up, low (abstain) below it.

## Served coefficients (per standard deviation; trained on every row)

| Signal | Weight | Expected | As expected |
|---|---|---|---|
| rerank_probability | +1.091 | + | yes |
| rerank_margin | -0.149 | + | no: never a reason |
| definition_mismatch | -0.520 | − | yes |
| data_age_years | +0.425 | − | no: never a reason |
| series_length | +0.185 | + | yes |
| boundary_distance | +0.024 | + | yes |
| fallback_steps | -0.194 | − | yes |

Intercept +1.781.

## Limitations

- The served reranker was fine-tuned on every dev claim (P4.3), so on these rows its probabilities and margins are in-sample: higher, and more often right, than on claims it has never seen. The model may lean on them more than it should; the held-out evaluation (P4.7) is the honest check of its calibration.
- About a hundred rows, most of them right: one claim moves the figures by about a point, and the threshold can move with them.
- Rows come from the runs named above; a run on backup models (a provider at its daily limit) has more wrong verdicts and more fallback steps than a usual day.
