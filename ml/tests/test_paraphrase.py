"""Paraphrase generation through the router, with a fake client (no network)."""

import asyncio
import json
from pathlib import Path

from holdsup.router import Router, Use, load_router_config
from holdsup.router.errors import ProviderUnavailable
from reranker.benchmark import Claim
from reranker.paraphrase import (
    BATCH,
    MAX_CHARS,
    PER_CLAIM,
    PROVIDERS,
    STEP,
    accept,
    generate,
    offline_config,
    prompt,
    read_rows,
    reword,
)
from tests.helpers import FakeChat, json_reply


def router(chat: FakeChat) -> Router:
    return Router(offline_config(load_router_config()), chat)


def by_key(claims: list[Claim], key: str) -> Claim:
    return next(c for c in claims if c.key == key)


def test_the_step_is_added_to_a_copy_gemini_first_and_never_shipped() -> None:
    shipped = load_router_config()
    config = offline_config(shipped)
    assert config.steps[STEP] == PROVIDERS and PROVIDERS[0] == "gemini-flash"
    assert STEP not in shipped.steps
    assert {k: v for k, v in config.steps.items() if k != STEP} == shipped.steps
    # Gemini serves it offline only; it never becomes a live candidate (D003).
    live = Router(config, FakeChat([])).candidates(STEP, Use.LIVE, set())
    assert all("gemini" not in p.name for p in live)


def test_accept_keeps_distinct_new_one_line_rewordings(claims: list[Claim]) -> None:
    claim = by_key(claims, "d1#1")
    proposed = [
        "",
        "ITALY'S UNEMPLOYMENT RATE WAS 8% IN 2022.",  # the claim itself
        "Italian  joblessness\nwas 8% in 2022",
        "Italian joblessness was 8% in 2022",  # a repeat once spaces are collapsed
        "x" * (MAX_CHARS + 1),
        "One in twelve Italians in the labour force had no job in 2022 (8%)",
        "Italy: 8% out of work in 2022",
        "In 2022, 8% of Italy's workforce was unemployed",
        "a fifth one, over the limit",
    ]
    kept = accept(claim, proposed)
    assert kept[0] == "Italian joblessness was 8% in 2022"
    assert len(kept) == PER_CLAIM and "a fifth one, over the limit" not in kept


def test_the_prompt_carries_keys_and_quotes_only(claims: list[Claim]) -> None:
    sent = json.loads(prompt([by_key(claims, "d2#1")]))
    assert sent == [{"key": "d2#1", "claim": "Spain's youth unemployment rate was 30% in 2020"}]


def test_reword_keeps_answers_for_claims_it_was_given_once(claims: list[Claim]) -> None:
    batch = [by_key(claims, "d1#1"), by_key(claims, "d2#1")]
    reply = json_reply(
        {
            "claims": [
                {"key": "d1#1", "paraphrases": ["Italian joblessness was 8% in 2022"]},
                {"key": "d1#1", "paraphrases": ["answered twice"]},
                {"key": "zz#1", "paraphrases": ["a claim it was not given"]},
                {"key": "d2#1", "paraphrases": ["Young Spaniards: 30% jobless in 2020"]},
            ]
        }
    )
    rows = asyncio.run(reword(router(FakeChat([reply])), batch))
    assert [(r.claim, r.text) for r in rows] == [
        ("d1#1", "Italian joblessness was 8% in 2022"),
        ("d2#1", "Young Spaniards: 30% jobless in 2020"),
    ]
    assert {(r.provider, r.model) for r in rows} == {("gemini-flash", "gemini-3.5-flash")}


def answer_all(claims: list[Claim]) -> object:
    return {"claims": [{"key": c.key, "paraphrases": [f"{c.quote}, reworded"]} for c in claims]}


def test_generate_writes_dev_rows_and_a_rerun_resumes(claims: list[Claim], tmp_path: Path) -> None:
    out = tmp_path / "p.jsonl"
    dev = [c for c in claims if c.split == "dev"]
    assert len(dev) <= BATCH  # one call
    first = FakeChat([json_reply(answer_all(dev[:2]))])  # the model skipped three claims
    assert asyncio.run(generate(router(first), claims, out)) == 0
    assert [r.claim for r in read_rows(out)] == ["d1#1", "d2#1"]

    second = FakeChat([json_reply(answer_all(dev[2:]))])
    asyncio.run(generate(router(second), claims, out))
    [(_, request)] = second.requests
    asked = [c["key"] for c in json.loads(str(request.messages[-1]["content"]))]
    assert asked == ["d2#2", "d3#1", "d4#1"]  # only what was left, never a test claim
    assert [r.claim for r in read_rows(out)] == [c.key for c in dev]


def test_generate_stops_when_no_provider_answers(claims: list[Claim], tmp_path: Path) -> None:
    out = tmp_path / "p.jsonl"
    chat = FakeChat([ProviderUnavailable("503"), ProviderUnavailable("503")])
    left = asyncio.run(generate(router(chat), claims, out))
    assert left == len([c for c in claims if c.split == "dev"])
    assert not out.exists()
