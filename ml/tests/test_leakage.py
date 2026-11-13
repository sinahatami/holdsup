"""P4.3's "Done when": no held-out claim, nor a paraphrase of one, is in the training data.

Three layers: the guard every path into training goes through, the builders that use it, and
the committed files (the paraphrases trained on and the report naming every training claim)
checked against the real benchmark.
"""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from holdsup.catalog.schema import Catalog
from holdsup.router import Router, load_router_config
from reranker import CLAIMS, PARAPHRASES, REPORTS
from reranker.benchmark import Claim, load_claims
from reranker.dataset import build_groups, pairs
from reranker.leakage import LeakageError, check_training_sentences, normalize
from reranker.paraphrase import Paraphrase, generate, offline_config, read_rows
from tests.helpers import UNEMPLOYMENT, FakeChat, FixedSearch, json_reply

POOL = [(UNEMPLOYMENT, 0.9)]


def row(claim: str, text: str) -> Paraphrase:
    return Paraphrase(claim=claim, text=text, provider="fake", model="fake")


# --- the guard -----------------------------------------------------------------------------------


def test_a_paraphrase_of_a_held_out_claim_is_refused(claims: list[Claim]) -> None:
    with pytest.raises(LeakageError, match="t1#1 is a held-out claim"):
        check_training_sentences([("t1#1", "French government debt hit 99% of GDP")], claims)


def test_a_sentence_equal_to_a_held_out_one_is_refused_whatever_its_claim(
    claims: list[Claim],
) -> None:
    # A dev claim's "paraphrase" that is in fact a test sentence (other case, a full stop).
    with pytest.raises(LeakageError, match="is a held-out sentence"):
        check_training_sentences([("d1#1", "FRANCE'S PUBLIC DEBT WAS 99% OF GDP IN 2017.")], claims)


def test_a_held_out_text_is_refused_not_only_its_quote(claims: list[Claim]) -> None:
    test_text = next(c.text for c in claims if c.key == "t1#1")
    with pytest.raises(LeakageError):
        check_training_sentences([("d1#1", test_text)], claims)


def test_an_unknown_claim_is_refused_and_every_problem_is_listed(claims: list[Claim]) -> None:
    with pytest.raises(LeakageError) as caught:
        check_training_sentences([("x9#1", "a"), ("t2#1", "b")], claims)
    assert len(caught.value.problems) == 2


def test_dev_sentences_pass(claims: list[Claim]) -> None:
    check_training_sentences([("d1#1", "Italian joblessness stood at 8% in 2022")], claims)


def test_normalize_ignores_case_spacing_and_closing_punctuation() -> None:
    assert normalize("  Spain's  rate was 5%  in 2020. ") == normalize(
        "spain's rate was 5% in 2020"
    )
    assert normalize("rate was 5%") != normalize("rate was 6%")


# --- the builders ----------------------------------------------------------------------------------


def test_the_dataset_holds_dev_claims_only(claims: list[Claim], catalog: Catalog) -> None:
    search = FixedSearch(POOL)
    groups = build_groups(
        claims, [row("d1#1", "Joblessness in Italy: 8% in 2022")], catalog, search
    )
    held_keys = {c.key for c in claims if c.split == "test"}
    held_text = {normalize(c.quote) for c in claims if c.split == "test"}
    assert groups
    assert all(g.query.claim.split == "dev" for g in groups)
    assert not {g.query.claim.key for g in groups} & held_keys
    assert not {normalize(p.query) for p in pairs(groups, catalog)} & held_text
    assert not {normalize(s) for s in search.asked} & held_text  # not even searched


def test_the_dataset_refuses_a_paraphrase_file_naming_a_test_claim(
    claims: list[Claim], catalog: Catalog
) -> None:
    with pytest.raises(LeakageError):
        build_groups(claims, [row("t1#1", "French debt: 99% of GDP")], catalog, FixedSearch(POOL))


def test_paraphrasing_sends_only_dev_claims_and_never_writes_a_held_out_sentence(
    claims: list[Claim], tmp_path: Path
) -> None:
    out = tmp_path / "paraphrases.jsonl"
    leaked = json_reply(
        {
            "claims": [
                {"key": "d1#1", "paraphrases": ["France's public debt was 99% of GDP in 2017"]}
            ]
        }
    )
    chat = FakeChat([leaked])
    router = Router(offline_config(load_router_config()), chat)
    with pytest.raises(LeakageError):
        asyncio.run(generate(router, claims, out))
    assert not out.exists()
    [(_, request)] = chat.requests
    sent = json.dumps(list(request.messages))
    assert "d1#1" in sent and "t1#1" not in sent and "France" not in sent


# --- the committed files ---------------------------------------------------------------------------


def test_committed_paraphrases_reword_dev_claims_only() -> None:
    benchmark = load_claims(CLAIMS)
    rows = read_rows(PARAPHRASES)
    assert rows
    check_training_sentences([(r.claim, r.text) for r in rows], benchmark)


def test_committed_report_names_dev_claims_only_and_the_committed_paraphrases() -> None:
    report = json.loads((REPORTS / "report.json").read_text(encoding="utf-8"))
    benchmark = load_claims(CLAIMS)
    dev_keys = {c.key for c in benchmark if c.split == "dev"}
    held_keys = {c.key for c in benchmark if c.split != "dev"}
    trained = set(report["training_claims"])
    assert trained
    assert not trained & held_keys
    assert trained <= dev_keys
    assert report["paraphrases_sha256"] == hashlib.sha256(PARAPHRASES.read_bytes()).hexdigest()
