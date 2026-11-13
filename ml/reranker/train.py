"""Fine-tune the cross-encoder and export it to ONNX. Needs the `train` group (`make ml-setup`).

A plain torch loop over the CrossEncoder's own model and tokenizer: pointwise binary
cross-entropy on (claim sentence, catalog entry) pairs, AdamW, linear warm-up then decay. It
needs no more than torch and sentence-transformers (the Trainer path would add `datasets` and
`accelerate`). Seeds are fixed; on CPU a run repeats exactly.
"""

import math
import random
import shutil
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import CrossEncoder
from transformers import PreTrainedModel

from reranker.dataset import Pair
from reranker.experiment import Hyper
from reranker.scorer import META_FILE, ONNX_FILE, TOKENIZER_FILE

INPUTS = ("input_ids", "attention_mask", "token_type_ids")  # BertForSequenceClassification's


class TorchReranker:
    def __init__(self, model: CrossEncoder, max_length: int) -> None:
        self.model = model
        self.max_length = max_length

    def logits(self, query: str, documents: Sequence[str]) -> list[float]:
        if not documents:
            return []
        scores = self.model.predict(
            [(query, d) for d in documents], batch_size=64, show_progress_bar=False
        )
        return [float(x) for x in np.asarray(scores).reshape(-1)]


def _load(hp: Hyper) -> CrossEncoder:
    torch.set_num_threads(hp.threads)
    model: CrossEncoder = CrossEncoder(
        hp.base_model,
        num_labels=1,
        max_length=hp.max_length,
        device="cpu",
        activation_fn=torch.nn.Identity(),  # raw logits; sigmoid is applied when ranking
    )
    return model


def _net(model: CrossEncoder) -> PreTrainedModel:
    """The transformers model inside (typed optional by sentence-transformers)."""
    if model.model is None:
        raise RuntimeError("the CrossEncoder has no underlying model")
    net: PreTrainedModel = model.model
    return net


def pretrained(hp: Hyper) -> TorchReranker:
    """The base model as published, not fine-tuned: the report's middle column."""
    model = _load(hp)
    _net(model).train(False)  # eval mode
    return TorchReranker(model, hp.max_length)


def fit(pairs: Sequence[Pair], hp: Hyper) -> TorchReranker:
    random.seed(hp.seed)
    np.random.seed(hp.seed)
    torch.manual_seed(hp.seed)
    model = _load(hp)
    net, tokenizer = _net(model), model.tokenizer
    no_decay = ("bias", "LayerNorm.weight")
    named = list(net.named_parameters())
    optimizer = torch.optim.AdamW(
        [
            {
                "params": [p for n, p in named if not any(x in n for x in no_decay)],
                "weight_decay": hp.weight_decay,
            },
            {"params": [p for n, p in named if any(x in n for x in no_decay)], "weight_decay": 0.0},
        ],
        lr=hp.learning_rate,
    )
    total = math.ceil(len(pairs) / hp.batch_size) * hp.epochs
    warm = max(1, int(total * hp.warmup))
    schedule = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lambda s: s / warm if s < warm else max(0.0, (total - s) / max(1, total - warm))
    )
    loss_fn = torch.nn.BCEWithLogitsLoss()
    order = list(range(len(pairs)))
    shuffle = random.Random(hp.seed)  # noqa: S311 - reproducible batches, not security
    net.train()
    for _ in range(hp.epochs):
        shuffle.shuffle(order)
        for start in range(0, len(order), hp.batch_size):
            batch = [pairs[i] for i in order[start : start + hp.batch_size]]
            encoded = tokenizer(
                [p.query for p in batch],
                [p.document for p in batch],
                padding=True,
                truncation=True,
                max_length=hp.max_length,
                return_tensors="pt",
            )
            logits = net(**encoded).logits.squeeze(-1)
            loss = loss_fn(logits, torch.tensor([p.label for p in batch], dtype=torch.float32))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            optimizer.step()
            schedule.step()
            optimizer.zero_grad()
    net.train(False)  # eval mode
    return TorchReranker(model, hp.max_length)


def save(model: TorchReranker, folder: Path) -> None:
    """The sentence-transformers folder, as it would be published on the Hub."""
    model.model.save_pretrained(str(folder))


def export_onnx(model: TorchReranker, folder: Path) -> tuple[str, int]:
    """model.onnx and tokenizer.json into `folder`; returns the pad token and its id."""
    folder.mkdir(parents=True, exist_ok=True)
    net, tokenizer = _net(model.model), model.model.tokenizer
    sample = tokenizer(["a claim"], ["a statistic"], return_tensors="pt")
    dynamic = {name: {0: "batch", 1: "sequence"} for name in INPUTS}
    with torch.no_grad():
        torch.onnx.export(
            net,
            tuple(sample[name] for name in INPUTS),
            str(folder / ONNX_FILE),
            input_names=list(INPUTS),
            output_names=["logits"],
            dynamic_axes={**dynamic, "logits": {0: "batch"}},
            opset_version=17,
            dynamo=False,
        )
    tokenizer.backend_tokenizer.save(str(folder / TOKENIZER_FILE))
    return str(tokenizer.pad_token), int(tokenizer.pad_token_id)


def quantize(source: Path, target: Path) -> None:
    """int8 weights (dynamic quantization) beside the same tokenizer and metadata."""
    from onnxruntime.quantization import QuantType, quantize_dynamic

    target.mkdir(parents=True, exist_ok=True)
    quantize_dynamic(source / ONNX_FILE, target / ONNX_FILE, weight_type=QuantType.QInt8)
    for name in (TOKENIZER_FILE, META_FILE):
        shutil.copyfile(source / name, target / name)
