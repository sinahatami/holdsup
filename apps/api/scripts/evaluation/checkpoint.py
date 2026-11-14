"""A run's finished texts on disk, so a run that stops part-way can be resumed.

The dev split is about 400 model calls on rate-limited providers: more than a day of the free
quota, and long enough to be stopped (out of memory, the machine sleeps). Each text that ran is
appended to `<name>.partial.jsonl`, beside the report, as soon as it is scored, with the model
calls and series requests it made. `--resume` keeps those texts and runs the rest, including
any the router could not serve; the report then covers every text, and the file is removed.

The first line says what the run is: benchmark, split, provider and versions. A partial run is
resumed only by a run of the same thing, so a report never mixes two pipelines or benchmarks.
"""

from pathlib import Path
from typing import Self

from pydantic import BaseModel, ValidationError

from scripts.evaluation.report import Stamp
from scripts.evaluation.run import TextRun


class CheckpointError(Exception):
    """The partial run cannot be resumed; the message says why."""


class Header(BaseModel):
    name: str
    benchmark: str  # the claims file's name
    split: str
    provider: str
    use: str
    versions: Stamp


def checkpoint_path(out_dir: Path, name: str) -> Path:
    return out_dir / f"{name}.partial.jsonl"


class Checkpoint:
    def __init__(self, path: Path, header: Header, done: dict[str, TextRun]) -> None:
        self.path = path
        self.header = header
        self.done = done  # text id -> its run; only texts that ran

    @classmethod
    def start(cls, path: Path, header: Header) -> Self:
        """A new partial run at `path`, replacing any there."""
        return cls._write(path, header, {})

    @classmethod
    def resume(cls, path: Path, header: Header) -> Self:
        """The partial run at `path`, or a new one when there is none. Raises CheckpointError
        when the file is a partial run of something else, or is damaged before its last line
        (the last line may have been cut short by whatever stopped the run: it is dropped)."""
        if not path.exists():
            return cls.start(path, header)
        lines = path.read_text(encoding="utf-8").splitlines()
        try:
            saved = Header.model_validate_json(lines[0]) if lines else None
        except ValidationError:
            saved = None
        if saved is None:
            raise CheckpointError(f"{path}: not a partial run (no header line)")
        if saved != header:
            raise CheckpointError(
                f"{path.name} is a partial run of another run ({_differences(saved, header)}): "
                "run without --resume to start over"
            )
        done: dict[str, TextRun] = {}
        for number, line in enumerate(lines[1:], 2):
            try:
                run = TextRun.model_validate_json(line)
            except ValidationError as exc:
                if number == len(lines):
                    break
                raise CheckpointError(
                    f"{path.name}:{number}: damaged ({exc.errors()[0]['msg']})"
                ) from exc
            done[run.outcome.id] = run
        return cls._write(path, header, done)  # without a line cut short, before appending

    @classmethod
    def _write(cls, path: Path, header: Header, done: dict[str, TextRun]) -> Self:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [header.model_dump_json(), *(run.model_dump_json() for run in done.values())]
        draft = path.with_name(path.name + ".tmp")
        draft.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
        draft.replace(path)  # all or nothing: a stop here leaves the old file whole
        return cls(path, header, done)

    def record(self, run: TextRun) -> None:
        """Keep a text that ran. One the router could not serve is not kept: a resumed run
        tries it again."""
        if run.outcome.error is not None:
            return
        self.done[run.outcome.id] = run
        with self.path.open("a", encoding="utf-8") as file:
            file.write(run.model_dump_json() + "\n")

    def remove(self) -> None:
        self.path.unlink(missing_ok=True)


def _differences(saved: Header, now: Header) -> str:
    was, found = _flat(saved.model_dump()), _flat(now.model_dump())
    return "; ".join(
        f"{key} {was.get(key)!r} there, {found.get(key)!r} now"
        for key in sorted(was.keys() | found.keys())
        if was.get(key) != found.get(key)
    )


def _flat(fields: dict[str, object], prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in fields.items():
        if isinstance(value, dict):
            out |= _flat(value, f"{prefix}{key}.")
        else:
            out[f"{prefix}{key}"] = value
    return out
