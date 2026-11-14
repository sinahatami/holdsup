"""A stopped run's finished texts on disk: what is kept, what is resumed, what is refused."""

from pathlib import Path

import pytest
from scripts.evaluation.checkpoint import Checkpoint, CheckpointError, Header, checkpoint_path
from scripts.evaluation.meter import Call
from scripts.evaluation.report import Stamp
from scripts.evaluation.run import TextRun
from scripts.evaluation.score import not_run, score_text

from tests.evaluation.helpers import label, output, result, text

HEADER = Header(
    name="dev",
    benchmark="claims.jsonl",
    split="dev",
    provider="router",
    use="live",
    versions=Stamp(app="0.1.0", catalog="1.0.0", tolerances=5, eval="0.1.0"),
)


def ran(id: str) -> TextRun:
    outcome = score_text(
        text(id, "x", label()),
        output(result()),
        {0: ["unemployment_rate_monthly"]},
        seconds=1.5,
        model_calls=2,
    )
    calls = [
        Call(
            "extract", "groq", "m", ok=False, latency_ms=3.0, error="RateLimited", daily_limit=True
        ),
        Call("extract", "mistral", "m", ok=True, latency_ms=9.5, prompt_tokens=40),
    ]
    return TextRun(outcome=outcome, calls=calls, series_requests=2, series_fetches=1)


def unserved(id: str) -> TextRun:
    return TextRun(outcome=not_run(text(id, "x", label()), "router: out", 0.5, 1), calls=[])


def test_the_file_sits_beside_the_report_under_its_name(tmp_path: Path) -> None:
    assert checkpoint_path(tmp_path, "dev.groq") == tmp_path / "dev.groq.partial.jsonl"


def test_texts_that_ran_come_back_whole_and_unserved_ones_are_run_again(tmp_path: Path) -> None:
    path = tmp_path / "dev.partial.jsonl"
    checkpoint = Checkpoint.start(path, HEADER)

    checkpoint.record(ran("a"))
    checkpoint.record(unserved("b"))
    checkpoint.record(ran("c"))

    back = Checkpoint.resume(path, HEADER)
    assert list(back.done) == ["a", "c"]
    assert back.done["a"] == ran("a")  # the outcome, every call and the series counts


def test_resuming_with_nothing_saved_starts_a_new_partial_run(tmp_path: Path) -> None:
    path = tmp_path / "out" / "dev.partial.jsonl"

    checkpoint = Checkpoint.resume(path, HEADER)

    assert checkpoint.done == {}
    assert path.read_text(encoding="utf-8") == HEADER.model_dump_json() + "\n"


def test_starting_replaces_an_earlier_partial_run(tmp_path: Path) -> None:
    path = tmp_path / "dev.partial.jsonl"
    Checkpoint.start(path, HEADER).record(ran("a"))

    Checkpoint.start(path, HEADER)

    assert Checkpoint.resume(path, HEADER).done == {}


def test_a_partial_run_of_another_version_is_not_resumed_and_is_left_alone(
    tmp_path: Path,
) -> None:
    path = tmp_path / "dev.partial.jsonl"
    Checkpoint.start(path, HEADER).record(ran("a"))
    before = path.read_text(encoding="utf-8")
    newer = HEADER.model_copy(
        update={"versions": HEADER.versions.model_copy(update={"eval": "0.2.0"})}
    )

    with pytest.raises(CheckpointError) as error:
        Checkpoint.resume(path, newer)

    assert "versions.eval '0.1.0' there, '0.2.0' now" in str(error.value)
    assert "run without --resume to start over" in str(error.value)
    assert path.read_text(encoding="utf-8") == before


def test_a_last_line_cut_short_by_the_stop_is_dropped_and_the_file_mended(tmp_path: Path) -> None:
    path = tmp_path / "dev.partial.jsonl"
    checkpoint = Checkpoint.start(path, HEADER)
    checkpoint.record(ran("a"))
    checkpoint.record(ran("b"))
    path.write_text(path.read_text(encoding="utf-8")[:-60], encoding="utf-8")

    back = Checkpoint.resume(path, HEADER)
    assert list(back.done) == ["a"]

    back.record(ran("c"))  # appended after a whole line, not onto the torn one
    assert list(Checkpoint.resume(path, HEADER).done) == ["a", "c"]


def test_a_damaged_line_before_the_last_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "dev.partial.jsonl"
    checkpoint = Checkpoint.start(path, HEADER)
    checkpoint.record(ran("a"))
    checkpoint.record(ran("b"))
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1][:-10]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(CheckpointError, match=r"dev\.partial\.jsonl:2: damaged"):
        Checkpoint.resume(path, HEADER)


@pytest.mark.parametrize("content", ["", "not json\n", '{"name": "dev"}\n'])
def test_a_file_without_a_header_is_not_a_partial_run(tmp_path: Path, content: str) -> None:
    path = tmp_path / "dev.partial.jsonl"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(CheckpointError, match="not a partial run"):
        Checkpoint.resume(path, HEADER)


def test_remove_deletes_the_file_and_is_safe_to_repeat(tmp_path: Path) -> None:
    path = tmp_path / "dev.partial.jsonl"
    checkpoint = Checkpoint.start(path, HEADER)

    checkpoint.remove()
    checkpoint.remove()

    assert not path.exists()
    assert list(tmp_path.iterdir()) == []  # no draft left behind either
