"""The indicator reranker: a small cross-encoder that reorders the catalog search's top 8.

Modules: `benchmark` (the dev split as training needs it), `leakage` (the held-out guard),
`paraphrase` (offline rewordings through the router), `dataset` (query groups with hard
negatives), `folds`, `metrics`, `experiment` (cross-validation, final fit, report), `scorer`
(the exported ONNX model, no torch), `train` (torch; the `train` group only), `report`.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CLAIMS = REPO / "eval" / "claims.jsonl"
EVAL_VERSION = REPO / "eval" / "VERSION"
CATALOG = REPO / "packages" / "catalog"
PARAPHRASES = HERE / "data" / "paraphrases.jsonl"
ARTIFACTS = HERE / "artifacts"  # gitignored: the trained model and its ONNX export
REPORTS = HERE / "reports"
MODEL_CARD = HERE / "MODEL_CARD.md"
