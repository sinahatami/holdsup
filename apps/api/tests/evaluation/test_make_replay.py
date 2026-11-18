"""`make eval` and `make eval-smoke` replay saved model replies unless the command says otherwise.

Checked on the recipe `make -n` would run: nothing is executed and no model is asked.
"""

import shutil
import subprocess

import pytest

from holdsup.config import REPO_ROOT

MAKE = shutil.which("make")
pytestmark = pytest.mark.skipif(MAKE is None, reason="make is not installed")


def recipe(target: str, args: str = "") -> str:
    assert MAKE is not None
    done = subprocess.run(  # noqa: S603  # our own make, our own Makefile, fixed arguments
        [MAKE, "-n", "-C", str(REPO_ROOT), target, f"ARGS={args}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def test_dev_run_replays_from_its_own_folder() -> None:
    assert "--replay .cache/eval-replies-dev" in recipe("eval")
    assert "--replay .cache/eval-replies-dev" in recipe("eval", "--resume")


def test_smoke_run_replays_from_its_own_folder() -> None:
    # A whole run prunes the replies it did not use, so the two sets never share a folder.
    assert "--replay .cache/eval-replies " in recipe("eval-smoke")
    assert ".cache/eval-replies-dev" not in recipe("eval-smoke")


@pytest.mark.parametrize("target", ["eval", "eval-smoke"])
@pytest.mark.parametrize("args", ["--record /x", "--replay /y"])
def test_an_explicit_folder_is_the_only_one(target: str, args: str) -> None:
    out = recipe(target, args)
    assert out.count("--replay") + out.count("--record") == 1
    assert ".cache/eval-replies" not in out


def test_the_held_out_run_asks_afresh_unless_told_otherwise() -> None:
    out = recipe("eval", "--split test --final")
    assert "--replay" not in out and "--record" not in out


def test_the_baseline_is_always_measured_afresh() -> None:
    out = recipe("eval-baseline")
    assert "--replay" not in out and "--record" not in out
