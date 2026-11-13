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
make reranker-fetch        # or: download the served export (the pinned Hub commit) -> reranker/artifacts/onnx/
```

- **Data.** The dev split of `eval/claims.jsonl` only. Every sentence that reaches training passes `reranker/leakage.py`, which refuses a held-out claim, a paraphrase keyed to one, and any sentence equal to a held-out quote or text; `tests/test_leakage.py` also checks the committed paraphrases and the report's list of training claims.
- **Committed:** the paraphrases (regenerating them costs quota and gives other sentences), `reports/report.{json,md}` (data versions and hashes, seed, cross-validated metrics, latency, ONNX checksums), `MODEL_CARD.md`.
- **Not committed:** `reranker/artifacts/` (the sentence-transformers folder, `onnx/` and `int8/` exports, about 200 MB). `make reranker-train` regenerates them from the committed paraphrases with the fixed seed; the checksums in the report tell whether a rebuild matches (expect that only on the same CPU and library versions).
- **Served:** the fp32 export pinned in `apps/api/holdsup/ml/reranker_pin.json`: a Hugging Face Hub repo, a commit hash and each file's sha256 (D030). The API image downloads it at build time; local runs and the eval load `reranker/artifacts/onnx/` after the same checksum check, so a retrain is not served until its export is uploaded and the pin's revision and checksums are updated together. `python -m reranker.fixture DIR` rebuilds the API's tiny test model.

## Confidence model (`confidence/`)

A logistic regression that turns signals the check already has (the reranker's probability and margin, a definition mismatch, the data's age, the series' length, how close the figure is to the tolerance's edge, backup models doing the work) into the chance a verdict is right. Below a threshold the result page says "can't check confidently" and why (D032). Report: `confidence/reports/report.md` (after the first training run).

```bash
make eval                 # a dev-split run: each claim's signals and whether its verdict was right
make confidence-train     # cross-validate, choose the threshold, export -> apps/api/holdsup/ml/confidence_model.json
make confidence-train ARGS="--report eval/reports/dev.json --report eval/reports/dev.mistral.json"   # several runs
```

- **Data.** Rows come from dev-split evaluation reports only: `confidence/dataset.py` refuses a report of another split and any held-out claim. Claims with a cant_check verdict are not rows (nothing to abstain from).
- **Served:** the exported JSON, read by `apps/api/holdsup/ml/confidence.py` in plain Python (no scikit-learn in the API). `tests/test_confidence.py` checks it scores exactly as scikit-learn does.
- **Committed:** the model JSON and `confidence/reports/report.{json,md}`; both are small and rebuilt from the named reports (their sha256 is recorded) with the fixed seed.
