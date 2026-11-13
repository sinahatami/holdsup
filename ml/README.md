# ml/

Training code (reranker, confidence model). It has its own environment and never ships in the API image.
Inference-only code lives in `apps/api/holdsup/ml/`.

`ml/` is a uv project of its own (`pyproject.toml`, `uv.lock`), outside the root workspace. Its default environment has `holdsup` (catalog, embeddings, router) and the test tools; the training libraries (torch CPU wheels, sentence-transformers, onnx) are in the `train` group, which only `make ml-setup` installs. `make test` and `make lint` cover `ml/` without them.

## Reranker (`reranker/`)

A cross-encoder that reorders the catalog search's top 8 for a claim. Report: [`reranker/reports/report.md`](reranker/reports/report.md); model card: [`reranker/MODEL_CARD.md`](reranker/MODEL_CARD.md).

```bash
make ml-setup              # once: the train group (about 1 GB)
make reranker-paraphrase   # reword the dev claims (offline; Gemini, else Groq; resumes) -> reranker/data/paraphrases.jsonl
make reranker-train        # cross-validate, train, export -> reranker/artifacts/, reports/, MODEL_CARD.md
make reranker-train ARGS="--quick /tmp/rr"   # every step in a few minutes, on a slice (checks the code)
```

- **Data.** The dev split of `eval/claims.jsonl` only. Every sentence that reaches training passes `reranker/leakage.py`, which refuses a held-out claim, a paraphrase keyed to one, and any sentence equal to a held-out quote or text; `tests/test_leakage.py` also checks the committed paraphrases and the report's list of training claims.
- **Committed:** the paraphrases (regenerating them costs quota and gives other sentences), `reports/report.{json,md}` (data versions and hashes, seed, cross-validated metrics, latency, ONNX checksums), `MODEL_CARD.md`.
- **Not committed:** `reranker/artifacts/` (the sentence-transformers folder, `onnx/` and `int8/` exports, about 200 MB). `make reranker-train` regenerates them from the committed paraphrases with the fixed seed; the checksums in the report tell whether a rebuild matches (expect that only on the same CPU and library versions).
