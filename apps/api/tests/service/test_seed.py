"""The gallery seeding: features good results, skips failures, and reruns from the ledger."""

from pathlib import Path

from holdsup.adapters.base import SourceUnavailable
from holdsup.config import REPO_ROOT
from holdsup.service.seed import format_table, read_claims, seed_gallery
from tests.service.fakes import (
    TEXT,
    FakeFetcher,
    claim_json,
    extraction,
    happy_script,
    make_runner,
    match_answer,
)


def test_read_claims_skips_comments_and_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "claims.txt"
    path.write_text("# a comment\n\n  First claim 5%.  \nSecond claim 7%.\n", encoding="utf-8")
    assert read_claims(path) == ["First claim 5%.", "Second claim 7%."]


def test_the_curated_list_has_ten_claims() -> None:
    claims = read_claims(REPO_ROOT / "eval" / "gallery_claims.txt")
    assert len(claims) == 10 and len(set(claims)) == 10
    assert all(len(c) <= 2000 for c in claims)


async def test_a_good_result_is_featured_and_listed_in_the_gallery() -> None:
    runner, _, store = make_runner(happy_script())
    outcomes = await seed_gallery(runner, store, [TEXT])
    assert [o.featured for o in outcomes] == [True]
    assert outcomes[0].verdicts
    gallery = await store.gallery(10)
    assert [g.id for g in gallery] == [outcomes[0].check_id]
    assert "1/1 claims featured" in format_table(outcomes)


async def test_a_rerun_reuses_the_ledger_with_no_model_call() -> None:
    runner, client, store = make_runner(happy_script())
    await seed_gallery(runner, store, [TEXT])
    calls = len(client.calls)
    first = [g.id for g in await store.gallery(10)]
    again = await seed_gallery(runner, store, [TEXT])
    assert again[0].featured and len(client.calls) == calls
    # The rerun's copy has its own link and replaces the earlier one in the gallery.
    assert [g.id for g in await store.gallery(10)] == [again[0].check_id] != first


async def test_force_checks_again_even_with_a_current_ledger_entry() -> None:
    runner, client, store = make_runner(happy_script() * 2)
    [first] = await seed_gallery(runner, store, [TEXT])
    calls = len(client.calls)
    [forced] = await seed_gallery(runner, store, [TEXT], force=True)
    assert len(client.calls) > calls  # models were called again
    after_forced = len(client.calls)
    assert forced.check_id != first.check_id
    assert [g.id for g in await store.gallery(10)] == [forced.check_id]
    # The forced result is now the newest ledger entry: a plain rerun copies it.
    [plain] = await seed_gallery(runner, store, [TEXT])
    assert len(client.calls) == after_forced and plain.featured


async def test_other_featured_checks_are_left_alone() -> None:
    runner, _, store = make_runner(happy_script() * 2)
    [other] = await seed_gallery(runner, store, ["Italy's unemployment rate fell 4 points."])
    await seed_gallery(runner, store, [TEXT])
    assert {g.id for g in await store.gallery(10)} >= {other.check_id}


async def test_a_result_with_a_source_down_is_not_featured() -> None:
    script = [extraction(claim_json()), match_answer()]
    runner, _, store = make_runner(script, fetcher=FakeFetcher(error=SourceUnavailable("503")))
    outcomes = await seed_gallery(runner, store, [TEXT])
    assert not outcomes[0].featured and "retryable" in outcomes[0].note
    assert await store.gallery(10) == []
    assert "0/1 claims featured" in format_table(outcomes)


async def test_a_claim_over_the_limit_is_reported_not_raised() -> None:
    runner, _, store = make_runner(happy_script() * 3)
    runner.limiter.limit = 1
    outcomes = await seed_gallery(runner, store, [TEXT, "Another claim: 5% of GDP in 2020."])
    assert outcomes[0].featured
    assert not outcomes[1].featured and outcomes[1].check_id is None
