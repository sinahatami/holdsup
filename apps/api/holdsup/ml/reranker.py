"""The indicator reranker: P4.3's fine-tuned cross-encoder, scored with onnxruntime and
tokenizers (both come with fastembed, D029), never torch.

An export folder holds `model.onnx`, `tokenizer.json` and `reranker.json` (how to feed the
model, and what it was made from). The export served is pinned in `reranker_pin.json`: the
Hugging Face Hub repo and commit it comes from, and each file's sha256 (D030). The image
build downloads those files (`scripts/fetch_reranker.py`); local runs and the eval use
ml/reranker/artifacts/onnx/. Either way `load_reranker` checks every checksum first. The API
never downloads anything.

ml/reranker/ trains and exports the model and measures its latency with this same code.
"""

import hashlib
import math
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field, field_validator
from tokenizers import Tokenizer

ONNX_FILE = "model.onnx"
TOKENIZER_FILE = "tokenizer.json"
META_FILE = "reranker.json"
EXPORT_FILES = frozenset({ONNX_FILE, TOKENIZER_FILE, META_FILE})
PIN_FILE = Path(__file__).with_name("reranker_pin.json")
# Hugging Face Spaces' free CPU has 2 cores; the report's latency is measured at 2 threads.
THREADS = 2
# How receipts name the reranker beside the router's providers.
PROVIDER = "local"
LABEL = "HoldsUp reranker (fine-tuned MiniLM)"
UNPINNED = "unpinned export"


class RerankerPin(BaseModel):
    """The export the API serves: a Hub model repo at one commit, and each file's sha256."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repo: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")  # a commit hash, never a branch name
    files: dict[str, str]  # file name -> sha256

    @field_validator("files")
    @classmethod
    def _every_export_file(cls, files: dict[str, str]) -> dict[str, str]:
        if set(files) != EXPORT_FILES:
            raise ValueError(f"the pin must list exactly {sorted(EXPORT_FILES)}")
        for name, digest in files.items():
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"{name}: not a lowercase hex sha256")
        return files

    @property
    def model(self) -> str:
        """How receipts name it: the repo at its short revision."""
        return f"{self.repo}@{self.revision[:7]}"


def load_pin(path: Path = PIN_FILE) -> RerankerPin:
    return RerankerPin.model_validate_json(path.read_text(encoding="utf-8"))


class RerankerFilesError(Exception):
    """An export folder that does not hold the pinned files."""


def sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_files(folder: Path, pin: RerankerPin) -> None:
    """Raise `RerankerFilesError` unless every pinned file is in `folder` with its sha256."""
    problems: list[str] = []
    for name, expected in sorted(pin.files.items()):
        path = folder / name
        if not path.is_file():
            problems.append(f"{name} is missing")
        elif (got := sha256(path)) != expected:
            problems.append(f"{name} has sha256 {got}, the pin says {expected}")
    if problems:
        raise RerankerFilesError(
            f"{folder} does not hold the reranker pinned in {PIN_FILE.name} ({pin.model}): "
            f"{'; '.join(problems)}. `make reranker-fetch` downloads the pinned files; after a "
            "retrain, upload the new export to the Hub and update the pin's revision and "
            "checksums together."
        )


class ExportMeta(BaseModel):
    """reranker.json: what serving needs to feed the model, and what the model was made from
    (ml/CLAUDE.md: data version, eval version, seed, metrics, date)."""

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


def sigmoid(x: float) -> float:
    """The probability a logit stands for (the model was trained with a sigmoid loss); the
    tanh form does not overflow for large negative logits."""
    return 0.5 * (1.0 + math.tanh(x / 2.0))


@dataclass
class OnnxReranker:
    session: Session
    tokenizer: Tokenizer
    inputs: tuple[str, ...]
    model: str = UNPINNED  # the pinned repo@revision when loaded by `load_reranker`
    # One claim at a time: the tokenizer is shared, and two runs on a 2-core CPU are no faster.
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @classmethod
    def load(cls, folder: Path, threads: int = THREADS, model: str = UNPINNED) -> "OnnxReranker":
        import onnxruntime as ort  # heavy import; only when the reranker is loaded

        meta = ExportMeta.model_validate_json((folder / META_FILE).read_text(encoding="utf-8"))
        tokenizer = pair_tokenizer(Tokenizer.from_file(str(folder / TOKENIZER_FILE)), meta)
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(
            str(folder / ONNX_FILE), options, providers=["CPUExecutionProvider"]
        )
        return cls(session, tokenizer, meta.inputs, model)

    def logits(self, query: str, documents: Sequence[str]) -> list[float]:
        """One raw score per document, higher is closer."""
        if not documents:
            return []
        with self._lock:
            encodings = self.tokenizer.encode_batch([(query, d) for d in documents])
            columns = {
                "input_ids": [e.ids for e in encodings],
                "attention_mask": [e.attention_mask for e in encodings],
                "token_type_ids": [e.type_ids for e in encodings],
            }
            feed = {name: np.asarray(columns[name], dtype=np.int64) for name in self.inputs}
            [logits] = self.session.run(["logits"], feed)
        return [float(x) for x in logits.reshape(len(documents), -1)[:, 0]]

    def probabilities(self, query: str, documents: Sequence[str]) -> list[float]:
        """Each document's probability of being the statistic the query is about."""
        return [sigmoid(x) for x in self.logits(query, documents)]


def load_reranker(
    folder: Path, pin: RerankerPin | None = None, threads: int = THREADS
) -> OnnxReranker:
    """The pinned export in `folder`, after checking every file's sha256 against the pin.
    Raises `RerankerFilesError` when a file is missing or is not the pinned one."""
    pin = pin or load_pin()
    verify_files(folder, pin)
    return OnnxReranker.load(folder, threads, model=pin.model)
