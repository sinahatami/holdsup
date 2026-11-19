"""`make eval-chatbot`: what it refuses, what it writes, and that it resumes."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from scripts.evaluation.chatbot import STEP, ChatRig
from scripts.evaluation.chatbot_cli import ChatRigFactory, main
from scripts.evaluation.meter import Meter, MeteredClient
from scripts.evaluation.patient import PatientRouter
from scripts.evaluation.report import Report

from holdsup.router import RouterConfig, load_router_config
from holdsup.router.client import ChatRequest, ChatResponse
from tests.evaluation.test_cli import benchmark, entry
from tests.router.fakes import FakeClient, FakeClock, config, provider

RIGHT = ChatResponse(content='{"verdicts": [{"claim": 1, "label": "supported"}]}')
FIRST = load_router_config().steps[STEP][0]  # the model a run asks unless told otherwise


def factory(
    *script: ChatResponse | Callable[[ChatRequest], ChatResponse],
    seen: list[RouterConfig] | None = None,
    budgets: list[float] | None = None,
) -> ChatRigFactory:
    @asynccontextmanager
    async def build(conf: RouterConfig, wait_budget_s: float) -> AsyncIterator[ChatRig]:
        if seen is not None:
            seen.append(conf)
        if budgets is not None:
            budgets.append(wait_budget_s)
        client = FakeClient()
        client.script("fake", script)
        meter = Meter()
        meter.step = STEP
        fake = config(provider("fake"), steps={STEP: ["fake"]})
        yield ChatRig(PatientRouter(fake, MeteredClient(client, meter), clock=FakeClock()), meter)

    return build


def run(tmp_path: Path, claims: Path, *flags: str, fake: ChatRigFactory) -> int:
    return main(["--claims", str(claims), "--out-dir", str(tmp_path / "out"), *flags], fake)


def test_a_run_asks_the_first_baseline_model_alone_and_names_the_report_after_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[RouterConfig] = []

    code = run(tmp_path, benchmark(tmp_path, entry()), fake=factory(RIGHT, seen=seen))

    out = capsys.readouterr()
    assert code == 0 and "1 claims in 1 texts: verdict accuracy 100%, 1 model calls" in out.out
    assert "extraction" not in out.out and "[1/1] r001: 1/1" in out.err
    # No failing over to another model when this one is rate-limited: the run waits for it.
    assert seen[0].steps[STEP] == (FIRST,)
    report = Report.model_validate_json(
        (tmp_path / "out" / f"dev.chatbot.{FIRST}.json").read_text()
    )
    assert (report.kind, report.provider, report.use, report.split) == (
        "chatbot",
        FIRST,
        "offline",  # offline tooling: the offline-only provider may answer
        "dev",
    )
    assert (tmp_path / "out" / f"dev.chatbot.{FIRST}.md").exists()
    assert not (tmp_path / "out" / f"dev.chatbot.{FIRST}.partial.jsonl").exists()


def test_the_held_out_split_is_refused_unless_the_run_is_final(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claims = benchmark(tmp_path, entry(split="test"))

    assert run(tmp_path, claims, "--split", "test", fake=factory()) == 2
    assert "held out for the final report" in capsys.readouterr().err
    assert run(tmp_path, claims, "--split", "test", "--final", fake=factory(RIGHT)) == 0
    assert (tmp_path / "out" / f"test.chatbot.{FIRST}.json").exists()


def test_another_provider_is_named_in_the_file_and_forced_for_the_step(tmp_path: Path) -> None:
    seen: list[RouterConfig] = []

    code = run(
        tmp_path,
        benchmark(tmp_path, entry()),
        "--provider",
        "mistral-ministral-14b",
        fake=factory(RIGHT, seen=seen),
    )

    assert code == 0 and seen[0].steps[STEP] == ("mistral-ministral-14b",)
    assert (tmp_path / "out" / "dev.chatbot.mistral-ministral-14b.json").exists()


def test_an_unknown_provider_and_an_empty_split_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claims = benchmark(tmp_path, entry())

    assert run(tmp_path, claims, "--provider", "nope", fake=factory()) == 2
    assert "unknown provider" in capsys.readouterr().err
    assert run(tmp_path, benchmark(tmp_path, entry(split="test")), fake=factory()) == 2
    assert "no texts in the dev split" in capsys.readouterr().err


def killed(_: ChatRequest) -> ChatResponse:
    raise RuntimeError("killed")


def test_a_stopped_run_resumes_and_asks_only_about_the_texts_left(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claims = benchmark(tmp_path, entry("r001"), entry("r002"))
    out = tmp_path / "out"
    # r001 is answered and kept; the run is stopped in r002 (the OOM killer, say).
    with pytest.raises(RuntimeError, match="killed"):
        run(tmp_path, claims, fake=factory(RIGHT, killed))
    name = f"dev.chatbot.{FIRST}"
    assert (out / f"{name}.partial.jsonl").exists() and not (out / f"{name}.json").exists()

    code = run(tmp_path, claims, "--resume", fake=factory(RIGHT))  # one answer: only r002 is asked

    assert code == 0
    assert "1 of 2 texts already ran" in capsys.readouterr().err
    report = Report.model_validate_json((out / f"{name}.json").read_text())
    assert report.metrics.texts == 2 and report.metrics.verdict.accuracy.rate == 1.0
    assert not (out / f"{name}.partial.jsonl").exists()


def test_the_wait_budget_reaches_the_rig_and_cannot_be_negative(tmp_path: Path) -> None:
    claims = benchmark(tmp_path, entry())
    budgets: list[float] = []

    assert run(tmp_path, claims, fake=factory(RIGHT, budgets=budgets)) == 0
    assert run(tmp_path, claims, "--wait-budget", "7200", fake=factory(RIGHT, budgets=budgets)) == 0
    assert budgets == [600.0, 7200.0]  # the default is ten minutes
    assert run(tmp_path, claims, "--wait-budget", "-1", fake=factory(RIGHT)) == 2
