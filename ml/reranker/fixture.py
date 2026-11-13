"""A tiny ONNX model with the reranker export's interface, for the API's tests (real
onnxruntime, no network, no download): three inputs in the export's order, one `logits`
output of shape [batch, 1].

    uv run --group train python -m reranker.fixture ../apps/api/tests/fixtures/reranker

It writes `model.onnx`, `tokenizer.json` (a word-level vocabulary) and `reranker.json`. A pair's
logit is (sum of the second segment's token ids) / 4 - 4, so a document made of later words
scores higher; the API's tests check those exact numbers. Needs `onnx` (the `train` group).
"""

import sys
from pathlib import Path

import onnx
from onnx import TensorProto, helper
from tokenizers import Tokenizer, models, pre_tokenizers, processors

from holdsup.ml.reranker import ONNX_FILE, TOKENIZER_FILE, ExportMeta
from reranker.scorer import write_meta

INPUTS = ("input_ids", "attention_mask", "token_type_ids")
VOCAB = {"[PAD]": 0, "[UNK]": 1, "[CLS]": 2, "[SEP]": 3, "debt": 4, "rate": 5, "gdp": 6}
SCALE, SHIFT = 0.25, -4.0
OPSET = 17


def graph_model() -> onnx.ModelProto:
    batch = ["batch", "tokens"]
    inputs = [helper.make_tensor_value_info(n, TensorProto.INT64, batch) for n in INPUTS]
    output = helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", 1])
    nodes = [
        helper.make_node("Mul", ["input_ids", "token_type_ids"], ["second"]),
        helper.make_node("Mul", ["second", "attention_mask"], ["kept"]),
        helper.make_node("Cast", ["kept"], ["kept_f"], to=TensorProto.FLOAT),
        helper.make_node("ReduceSum", ["kept_f", "axis"], ["total"], keepdims=1),
        helper.make_node("Mul", ["total", "scale"], ["scaled"]),
        helper.make_node("Add", ["scaled", "shift"], ["logits"]),
    ]
    constants = [
        helper.make_tensor("axis", TensorProto.INT64, [1], [1]),
        helper.make_tensor("scale", TensorProto.FLOAT, [], [SCALE]),
        helper.make_tensor("shift", TensorProto.FLOAT, [], [SHIFT]),
    ]
    graph = helper.make_graph(nodes, "tiny_reranker", inputs, [output], constants)
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid("", OPSET)],
        producer_name="holdsup-ml-fixture",
    )
    model.ir_version = 8  # readable by any onnxruntime the API might pin
    onnx.checker.check_model(model)
    return model


def tokenizer() -> Tokenizer:
    tok = Tokenizer(models.WordLevel(VOCAB, unk_token="[UNK]"))  # noqa: S106 - a token
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]",
        pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", 2), ("[SEP]", 3)],
    )
    return tok


def meta() -> ExportMeta:
    return ExportMeta(
        inputs=INPUTS,
        max_length=16,
        pad_id=0,
        pad_token="[PAD]",  # noqa: S106 - a token, not a password
        base_model="tiny fixture",
        eval_version="0.0.0",
        catalog_version="0.0.0",
        paraphrases_sha256="0" * 64,
        seed=0,
        created="2026-11-13",
        cv_top1=None,
        cv_mrr_at_8=None,
    )


def write(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ONNX_FILE).write_bytes(graph_model().SerializeToString())
    tokenizer().save(str(folder / TOKENIZER_FILE))
    write_meta(folder, meta())


if __name__ == "__main__":
    write(Path(sys.argv[1]))
