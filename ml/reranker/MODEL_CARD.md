---
language: en
license: apache-2.0
library_name: sentence-transformers
pipeline_tag: text-ranking
base_model: cross-encoder/ms-marco-MiniLM-L6-v2
tags: [cross-encoder, reranker, statistics, fact-checking, onnx]
---

# holdsup-indicator-reranker

A small cross-encoder that reranks candidate statistics for a numeric claim. Given a claim sentence ("Spain's youth unemployment rate was 55% in 2013") and the 8 catalog entries an embedding search found for it, it scores each pair so the statistic the claim is about comes first. It is part of HoldsUp, a statistical claim auditor, where a wide enough margin lets matching skip a language-model call.

## Use

```python
from sentence_transformers import CrossEncoder

model = CrossEncoder("sinahatami/holdsup-reranker")
scores = model.predict([(claim, entry) for entry in entries])  # logits
```

Scores are logits; a sigmoid turns them into 0..1. An entry is `name (unit). Also called: aliases. definition`. The ONNX exports (`model.onnx`, `tokenizer.json`, `reranker.json`) run with onnxruntime and tokenizers alone.

## Training data

- Benchmark eval 0.2.0, dev split only: 106 claims, 103 with a catalog statistic (55 distinct), catalog 0.8.0.
- 423 paraphrases of those claims, written offline by gemini-flash/gemini-3.5-flash (120), groq-gpt-oss-120b/openai/gpt-oss-120b (303).
- 529 query sentences; each is paired with the top 8 catalog entries the search shows for its place (one positive, the rest hard negatives). 12 queries had their statistic outside the top 8 and get it added as a positive for training only. 4244 training pairs in all.
- 5-fold cross-validation grouped by statistic and place (a sentence and its variants stay in one fold); quotes scored per fold: 22, 21, 21, 21, 21. Paraphrases train, never score.
- No held-out (test split) claim, nor a paraphrase of one, is in any of it: the dataset builder refuses them and ml/tests/test_leakage.py checks this report's claim list.

## Results

Cross-validated on the dev split (103 claims with a catalog statistic): top-1 94.2% against 68.9% for the embedding search alone, MRR@8 0.966 against 0.794.

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

| Export | Size | Median per claim | p95 per claim |
| --- | --: | --: | --: |
| fp32 | 91.0 MB | 161.6 ms | 207.5 ms |
| int8 | 23.0 MB | 152.2 ms | 192.8 ms |

Measured with onnxruntime on 2 CPU threads, 8.0 candidates per claim, 106 claims. The fp32 export scores as the torch model does (largest logit difference 5.7e-06). int8 puts the same statistic first on 98.1% of the dev quotes; its probabilities differ from fp32's by at most 0.163.

## Limits

- Trained on 106 English claims about European and world statistics (labour, economy, population, health, energy) and their paraphrases; it knows the 55 catalog entries those claims name best. Scores on statistics it never saw in training are in the table above.
- It ranks what the search found; it cannot recover a statistic outside the top 8.
- Paraphrases come from language models and keep each claim's numbers, place and period; real phrasings are more varied.
- The held-out test split of the benchmark was never used; the final evaluation on it is reported separately.
