"""The ONNX scoring path (the one P4.4 serves), with a tiny tokenizer and a fake session."""

from pathlib import Path

import numpy as np
import numpy.typing as npt
from tokenizers import Tokenizer, models, pre_tokenizers, processors

from reranker.scorer import (
    META_FILE,
    ExportMeta,
    OnnxReranker,
    measure,
    pair_tokenizer,
    write_meta,
)

INPUTS = ("input_ids", "attention_mask", "token_type_ids")


def meta(max_length: int = 32) -> ExportMeta:
    return ExportMeta(
        inputs=INPUTS,
        max_length=max_length,
        pad_id=0,
        pad_token="[PAD]",  # noqa: S106 - a token, not a password
        base_model="base",
        eval_version="0.2.0",
        catalog_version="0.8.0",
        paraphrases_sha256="0" * 64,
        seed=13,
        created="2026-11-13",
        cv_top1=0.9,
        cv_mrr_at_8=0.95,
    )


def tokenizer(max_length: int = 32) -> Tokenizer:
    vocab = {"[PAD]": 0, "[UNK]": 1, "[CLS]": 2, "[SEP]": 3, "debt": 4, "rate": 5, "gdp": 6}
    tok = Tokenizer(models.WordLevel(vocab, unk_token="[UNK]"))  # noqa: S106
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]",
        pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", 2), ("[SEP]", 3)],
    )
    return pair_tokenizer(tok, meta(max_length))


class FakeSession:
    def __init__(self) -> None:
        self.feeds: list[dict[str, npt.NDArray[np.int64]]] = []

    def run(
        self, output_names: list[str] | None, input_feed: dict[str, npt.NDArray[np.int64]]
    ) -> list[npt.NDArray[np.float32]]:
        self.feeds.append(input_feed)
        n = len(input_feed["input_ids"])
        return [np.arange(n, dtype=np.float32).reshape(n, 1)]


def test_logits_feed_padded_pairs_in_the_graph_s_input_order() -> None:
    session = FakeSession()
    reranker = OnnxReranker(session, tokenizer(), INPUTS)
    scores = reranker.logits("debt gdp", ["debt", "rate gdp debt"])
    assert scores == [0.0, 1.0]
    [feed] = session.feeds
    assert list(feed) == list(INPUTS)
    assert all(a.dtype == np.int64 and a.shape == feed["input_ids"].shape for a in feed.values())
    # [CLS] debt gdp [SEP] debt [SEP] [PAD] [PAD], second segment typed 1, padding masked.
    assert feed["input_ids"][0].tolist() == [2, 4, 6, 3, 4, 3, 0, 0]
    assert feed["token_type_ids"][0].tolist() == [0, 0, 0, 0, 1, 1, 0, 0]
    assert feed["attention_mask"][0].tolist() == [1, 1, 1, 1, 1, 1, 0, 0]


def test_long_pairs_are_truncated_to_max_length() -> None:
    session = FakeSession()
    OnnxReranker(session, tokenizer(max_length=6), INPUTS).logits("debt gdp", ["rate " * 20])
    assert session.feeds[0]["input_ids"].shape == (1, 6)


def test_no_documents_means_no_call() -> None:
    session = FakeSession()
    assert OnnxReranker(session, tokenizer(), INPUTS).logits("debt", []) == []
    assert session.feeds == []


def test_measure_reports_per_claim_latency() -> None:
    reranker = OnnxReranker(FakeSession(), tokenizer(), INPUTS)
    work = [("debt", ["debt", "rate"]), ("rate", ["gdp", "rate", "debt", "debt"])]
    lat = measure(reranker, work, threads=2, warmup=1)
    assert (lat.threads, lat.claims, lat.candidates_per_claim) == (2, 2, 3.0)
    assert 0 <= lat.p50_ms <= lat.p95_ms


def test_meta_round_trips(tmp_path: Path) -> None:
    write_meta(tmp_path, meta())
    assert ExportMeta.model_validate_json((tmp_path / META_FILE).read_text()) == meta()
