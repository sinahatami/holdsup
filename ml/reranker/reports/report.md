# Indicator reranker: report (2026-11-13)

Base model `cross-encoder/ms-marco-MiniLM-L6-v2` (a sentence-transformers CrossEncoder), fine-tuned with a plain PyTorch loop; seed 13.

## Data

- Benchmark eval 0.2.0, dev split only: 106 claims, 103 with a catalog statistic (55 distinct), catalog 0.8.0.
- 423 paraphrases of those claims, written offline by gemini-flash/gemini-3.5-flash (120), groq-gpt-oss-120b/openai/gpt-oss-120b (303).
- 529 query sentences; each is paired with the top 8 catalog entries the search shows for its place (one positive, the rest hard negatives). 12 queries had their statistic outside the top 8 and get it added as a positive for training only. 4244 training pairs in all.
- 5-fold cross-validation grouped by statistic and place (a sentence and its variants stay in one fold); quotes scored per fold: 22, 21, 21, 21, 21. Paraphrases train, never score.
- No held-out (test split) claim, nor a paraphrase of one, is in any of it: the dataset builder refuses them and ml/tests/test_leakage.py checks this report's claim list.

## Embedding search alone vs. the reranker (cross-validated on the dev split)

| Claims | Ranker | n | Top-1 | Recall@8 | MRR@8 |
| --- | --- | --: | --: | --: | --: |
| All | Embedding search alone | 103 | 68.9% | 99.0% | 0.794 |
| All | Base cross-encoder, not fine-tuned | 103 | 80.6% | 99.0% | 0.888 |
| All | Fine-tuned reranker | 103 | 94.2% | 99.0% | 0.966 |
| Statistic seen in training | Embedding search alone | 31 | 48.4% | 100.0% | 0.650 |
| Statistic seen in training | Base cross-encoder, not fine-tuned | 31 | 77.4% | 100.0% | 0.866 |
| Statistic seen in training | Fine-tuned reranker | 31 | 100.0% | 100.0% | 1.000 |
| Statistic not seen | Embedding search alone | 72 | 77.8% | 98.6% | 0.856 |
| Statistic not seen | Base cross-encoder, not fine-tuned | 72 | 81.9% | 98.6% | 0.897 |
| Statistic not seen | Fine-tuned reranker | 72 | 91.7% | 98.6% | 0.951 |

All three rank the same 8 candidates, so recall@8 is the search's ceiling and the same for each. Each claim is ranked by a model trained without its fold. A statistic is seen when some other claim about it was in that fold's training data.

## Margin (P4.4's skip-the-model rule)

Margin: the fine-tuned reranker's probability for the first candidate minus the second's. Claims with no catalog statistic count as wrong when answered.

| Margin at least | Claims answered without the model | Share | Top-1 right |
| --: | --: | --: | --: |
| 0.1 | 83 | 78.3% | 81 (97.6%) |
| 0.2 | 74 | 69.8% | 72 (97.3%) |
| 0.3 | 66 | 62.3% | 64 (97.0%) |
| 0.4 | 60 | 56.6% | 58 (96.7%) |
| 0.5 | 55 | 51.9% | 53 (96.4%) |
| 0.6 | 48 | 45.3% | 46 (95.8%) |
| 0.7 | 42 | 39.6% | 40 (95.2%) |
| 0.8 | 34 | 32.1% | 32 (94.1%) |
| 0.9 | 21 | 19.8% | 21 (100.0%) |

Claims with no catalog statistic: 3; the reranker's highest first-candidate probability on them: 0.000.

## CPU latency and export

| Export | Size | Median per claim | p95 per claim |
| --- | --: | --: | --: |
| fp32 | 91.0 MB | 161.6 ms | 207.5 ms |
| int8 | 23.0 MB | 152.2 ms | 192.8 ms |

Measured with onnxruntime on 2 CPU threads, 8.0 candidates per claim, 106 claims. The fp32 export scores as the torch model does (largest logit difference 5.7e-06). int8 puts the same statistic first on 98.1% of the dev quotes; its probabilities differ from fp32's by at most 0.163.

## Hyperparameters

- base_model: cross-encoder/ms-marco-MiniLM-L6-v2
- epochs: 2
- learning_rate: 3e-05
- batch_size: 32
- warmup: 0.1
- weight_decay: 0.01
- max_length: 256
- seed: 13
- threads: 6
