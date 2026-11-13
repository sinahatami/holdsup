"""The exported reranker, scored with onnxruntime and tokenizers alone (no torch).

These are the libraries the API already has through fastembed, so this is the code path P4.4
serves; the latency in the report is measured here. An export folder holds `model.onnx`,
`tokenizer.json` and `reranker.json` (how to feed it, and what it was trained on).
"""

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict
from tokenizers import Tokenizer

ONNX_FILE = "model.onnx"
TOKENIZER_FILE = "tokenizer.json"
META_FILE = "reranker.json"


class ExportMeta(BaseModel):
    """reranker.json: what serving needs to feed the model, and what the model was made from
    (data version, eval version, seed, metrics, date)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    inputs: tuple[str, ...]  # ONNX input names, in the order the graph declares them
    max_length: int
    pad_id: int
    pad_token: str
    base_model: str
    eval_version: str
    catalog_version: str
    paraphrases_sha256: str
    seed: int
    created: str
    cv_top1: float | None
    cv_mrr_at_8: float | None


class Session(Protocol):
    def run(
        self, output_names: list[str] | None, input_feed: dict[str, npt.NDArray[np.int64]]
    ) -> Sequence[npt.NDArray[np.float32]]: ...


def pair_tokenizer(tokenizer: Tokenizer, meta: ExportMeta) -> Tokenizer:
    """Truncate and pad pairs as training did (longest first, to the longest in the batch)."""
    tokenizer.enable_truncation(meta.max_length, strategy="longest_first")
    tokenizer.enable_padding(pad_id=meta.pad_id, pad_token=meta.pad_token)
    return tokenizer


@dataclass
class OnnxReranker:
    session: Session
    tokenizer: Tokenizer
    inputs: tuple[str, ...]

    @classmethod
    def load(cls, folder: Path, threads: int = 2) -> "OnnxReranker":
        import onnxruntime as ort

        meta = ExportMeta.model_validate_json((folder / META_FILE).read_text(encoding="utf-8"))
        tokenizer = pair_tokenizer(Tokenizer.from_file(str(folder / TOKENIZER_FILE)), meta)
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(
            str(folder / ONNX_FILE), options, providers=["CPUExecutionProvider"]
        )
        return cls(session, tokenizer, meta.inputs)

    def logits(self, query: str, documents: Sequence[str]) -> list[float]:
        """One raw score per document, higher is closer (sigmoid gives 0..1)."""
        if not documents:
            return []
        encodings = self.tokenizer.encode_batch([(query, d) for d in documents])
        columns = {
            "input_ids": [e.ids for e in encodings],
            "attention_mask": [e.attention_mask for e in encodings],
            "token_type_ids": [e.type_ids for e in encodings],
        }
        feed = {name: np.asarray(columns[name], dtype=np.int64) for name in self.inputs}
        [logits] = self.session.run(["logits"], feed)
        return [float(x) for x in logits.reshape(len(documents), -1)[:, 0]]


class Latency(BaseModel):
    threads: int
    claims: int
    candidates_per_claim: float
    p50_ms: float
    p95_ms: float
    mean_ms: float


def measure(
    reranker: OnnxReranker, work: Sequence[tuple[str, Sequence[str]]], threads: int, warmup: int = 5
) -> Latency:
    """Wall time to score each claim's candidates, after a few warm-up calls."""
    for query, docs in work[:warmup]:
        reranker.logits(query, docs)
    times: list[float] = []
    for query, docs in work:
        start = time.perf_counter()
        reranker.logits(query, docs)
        times.append((time.perf_counter() - start) * 1000)
    ordered = sorted(times)
    return Latency(
        threads=threads,
        claims=len(times),
        candidates_per_claim=sum(len(d) for _, d in work) / len(work),
        p50_ms=round(float(np.percentile(ordered, 50)), 2),
        p95_ms=round(float(np.percentile(ordered, 95)), 2),
        mean_ms=round(sum(times) / len(times), 2),
    )


def write_meta(folder: Path, meta: ExportMeta) -> None:
    (folder / META_FILE).write_text(json.dumps(meta.model_dump(), indent=2) + "\n")
