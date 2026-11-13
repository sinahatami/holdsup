"""The served reranker: the pin, the checksum check, and scoring with a tiny real ONNX model
(tests/fixtures/reranker, made by ml/reranker/fixture.py) or a fake session. No network."""

import shutil
import threading
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from pydantic import ValidationError

from holdsup.catalog.schema import load_catalog
from holdsup.config import REPO_ROOT
from holdsup.ml.reranker import (
    EXPORT_FILES,
    META_FILE,
    ONNX_FILE,
    PIN_FILE,
    TOKENIZER_FILE,
    UNPINNED,
    ExportMeta,
    OnnxReranker,
    RerankerFilesError,
    RerankerPin,
    load_pin,
    load_reranker,
    pair_tokenizer,
    sha256,
    sigmoid,
    verify_files,
)

TINY = Path(__file__).resolve().parents[1] / "fixtures" / "reranker"
REVISION = "0123456789abcdef0123456789abcdef01234567"
INPUTS = ("input_ids", "attention_mask", "token_type_ids")


def tiny_pin(folder: Path = TINY) -> RerankerPin:
    return RerankerPin(
        repo="someone/tiny-reranker",
        revision=REVISION,
        files={name: sha256(folder / name) for name in EXPORT_FILES},
    )


# --- the pin -----------------------------------------------------------------------------


def test_the_committed_pin_names_a_commit_and_every_export_file() -> None:
    pin = load_pin()
    assert PIN_FILE.name == "reranker_pin.json"
    assert pin.repo == "sinahatami/holdsup-reranker"
    assert pin.model == f"sinahatami/holdsup-reranker@{pin.revision[:7]}"
    assert set(pin.files) == {ONNX_FILE, TOKENIZER_FILE, META_FILE}


@pytest.mark.parametrize(
    ("change", "why"),
    [
        ({"revision": "main"}, "revision"),  # a branch can move; a commit cannot
        ({"revision": REVISION.upper()}, "revision"),
        ({"repo": "no-owner"}, "repo"),
        ({"files": {ONNX_FILE: "0" * 64}}, "exactly"),
        ({"files": dict.fromkeys(EXPORT_FILES, "x" * 64)}, "hex"),
        ({"files": dict.fromkeys(EXPORT_FILES, "0" * 63)}, "hex"),
        ({"extra": 1}, "extra"),
    ],
)
def test_a_pin_that_could_serve_other_bytes_is_rejected(
    change: dict[str, object], why: str
) -> None:
    good = tiny_pin().model_dump()
    with pytest.raises(ValidationError, match=why):
        RerankerPin.model_validate({**good, **change})


# --- the checksum check ------------------------------------------------------------------


def test_the_pinned_files_pass() -> None:
    verify_files(TINY, tiny_pin())


def test_a_missing_or_changed_file_is_refused(tmp_path: Path) -> None:
    shutil.copytree(TINY, tmp_path, dirs_exist_ok=True)
    pin = tiny_pin(tmp_path)
    (tmp_path / TOKENIZER_FILE).unlink()
    (tmp_path / META_FILE).write_text("{}")
    with pytest.raises(RerankerFilesError) as caught:
        verify_files(tmp_path, pin)
    message = str(caught.value)
    assert "tokenizer.json is missing" in message
    assert f"reranker.json has sha256 {sha256(tmp_path / META_FILE)}" in message
    assert "someone/tiny-reranker@0123456" in message and "make reranker-fetch" in message
    with pytest.raises(RerankerFilesError):
        load_reranker(tmp_path, pin)


# --- scoring with the tiny model ---------------------------------------------------------


def test_the_tiny_model_loads_with_its_pin_and_scores_pairs() -> None:
    reranker = load_reranker(TINY, tiny_pin(), threads=1)
    assert reranker.model == "someone/tiny-reranker@0123456"
    assert reranker.inputs == INPUTS
    # logit = (sum of the second segment's ids, its [SEP] included) / 4 - 4
    # "gdp rate" -> 6 + 5 + 3 = 14 -> -0.5; "debt" -> 4 + 3 = 7 -> -2.25; "" -> 3 -> -3.25
    assert reranker.logits("debt", ["gdp rate", "debt", ""]) == [-0.5, -2.25, -3.25]
    probabilities = reranker.probabilities("debt", ["gdp rate", "debt"])
    assert probabilities == pytest.approx([sigmoid(-0.5), sigmoid(-2.25)])
    assert probabilities[0] > probabilities[1]


def test_unpinned_load_says_so() -> None:
    assert OnnxReranker.load(TINY, threads=1).model == UNPINNED


def test_concurrent_calls_score_the_same() -> None:
    reranker = load_reranker(TINY, tiny_pin(), threads=1)
    results: list[list[float]] = []

    def score() -> None:
        results.append(reranker.logits("rate", ["gdp", "debt gdp rate", "rate"]))

    threads = [threading.Thread(target=score) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == [[-1.75, 0.5, -2.0]] * 8


def test_sigmoid_is_a_probability_and_never_overflows() -> None:
    assert sigmoid(0.0) == 0.5
    assert sigmoid(-1000.0) == 0.0 and sigmoid(1000.0) == 1.0
    assert sigmoid(2.0) == pytest.approx(1 / (1 + np.exp(-2.0)))


# --- the feed, with a fake session --------------------------------------------------------


class FakeSession:
    def __init__(self) -> None:
        self.feeds: list[dict[str, npt.NDArray[np.int64]]] = []

    def run(
        self, output_names: list[str] | None, input_feed: dict[str, npt.NDArray[np.int64]]
    ) -> list[npt.NDArray[np.float32]]:
        assert output_names == ["logits"]
        self.feeds.append(input_feed)
        n = len(input_feed["input_ids"])
        return [np.arange(n, dtype=np.float32).reshape(n, 1)]


def fake_reranker(session: FakeSession, max_length: int = 32) -> OnnxReranker:
    from tokenizers import Tokenizer

    meta = ExportMeta.model_validate_json((TINY / META_FILE).read_text())
    meta = meta.model_copy(update={"max_length": max_length})
    tokenizer = pair_tokenizer(Tokenizer.from_file(str(TINY / TOKENIZER_FILE)), meta)
    return OnnxReranker(session, tokenizer, INPUTS)


def test_logits_feed_padded_pairs_in_the_graph_s_input_order() -> None:
    session = FakeSession()
    assert fake_reranker(session).logits("debt gdp", ["debt", "rate gdp debt"]) == [0.0, 1.0]
    [feed] = session.feeds
    assert list(feed) == list(INPUTS)
    assert all(a.dtype == np.int64 and a.shape == feed["input_ids"].shape for a in feed.values())
    # [CLS] debt gdp [SEP] debt [SEP] [PAD] [PAD], second segment typed 1, padding masked.
    assert feed["input_ids"][0].tolist() == [2, 4, 6, 3, 4, 3, 0, 0]
    assert feed["token_type_ids"][0].tolist() == [0, 0, 0, 0, 1, 1, 0, 0]
    assert feed["attention_mask"][0].tolist() == [1, 1, 1, 1, 1, 1, 0, 0]


def test_long_pairs_are_truncated_to_max_length() -> None:
    session = FakeSession()
    fake_reranker(session, max_length=6).logits("debt gdp", ["rate " * 20])
    assert session.feeds[0]["input_ids"].shape == (1, 6)


def test_no_documents_means_no_call() -> None:
    session = FakeSession()
    assert fake_reranker(session).probabilities("debt", []) == []
    assert session.feeds == []


# --- the pinned export itself, when this checkout has it ----------------------------------

EXPORT = REPO_ROOT / "ml" / "reranker" / "artifacts" / "onnx"


@pytest.mark.skipif(not EXPORT.is_dir(), reason="no local export (make reranker-fetch)")
def test_the_pinned_export_loads_here_and_ranks_a_claim() -> None:
    """The bytes the image serves, under this environment's onnxruntime (the export was made
    with ml's): the right statistic first for a plain claim."""
    reranker = load_reranker(EXPORT)
    assert reranker.model == load_pin().model
    catalog = load_catalog(REPO_ROOT / "packages" / "catalog")
    ids = ["unemployment_rate_monthly", "youth_unemployment_rate_monthly", "neet_rate"]
    documents = [catalog.get(i).rerank_text() for i in ids]
    quote = "Youth unemployment in Italy is now 18.7%, the lowest since 2007."
    scores = reranker.probabilities(quote, documents)
    assert max(range(3), key=lambda i: scores[i]) == 1


# --- what the API does at start ------------------------------------------------------------


def test_the_api_matches_without_a_missing_export_but_refuses_a_wrong_one(tmp_path: Path) -> None:
    from holdsup.config import Settings
    from holdsup.service.wiring import optional_reranker

    assert optional_reranker(Settings(reranker_dir=tmp_path / "absent")) is None
    with pytest.raises(RerankerFilesError, match="sinahatami/holdsup-reranker@8f067c7"):
        optional_reranker(Settings(reranker_dir=TINY))  # not the pinned bytes
