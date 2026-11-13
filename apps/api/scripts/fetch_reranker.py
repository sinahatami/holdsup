"""Download the pinned reranker export from the Hugging Face Hub, checking each file's sha256
(D030).

    python fetch_reranker.py PIN DEST

PIN is holdsup/ml/reranker_pin.json. Each file comes from
https://huggingface.co/<repo>/resolve/<revision>/<file>, where the revision is a commit hash,
so the bytes cannot change under the same pin. A file already in DEST with the pinned sha256
is kept. A file with another sha256 (a local retrain, say) is never overwritten: the script
stops and says so. A download that does not match the pin fails the run, and nothing
half-written is left under the file's name.

Standard library only: the image's `reranker` stage runs it on a bare Python image, so that
layer is downloaded again only when the pin changes. `make reranker-fetch` runs it for a
local checkout. The API itself never downloads.
"""

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import BinaryIO, cast
from urllib.request import Request, urlopen

HUB = "https://huggingface.co"
CHUNK = 1 << 20

Opener = Callable[[str], BinaryIO]


class FetchError(Exception):
    pass


def read_pin(path: Path) -> tuple[str, str, dict[str, str]]:
    """The pin's repo, revision and file -> sha256."""
    pin = json.loads(path.read_text(encoding="utf-8"))
    repo, revision, files = pin["repo"], pin["revision"], pin["files"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise FetchError(f"{path}: the revision must be a 40-hex commit hash, not {revision!r}")
    return repo, revision, files


def file_url(repo: str, revision: str, name: str) -> str:
    return f"{HUB}/{repo}/resolve/{revision}/{name}"


def sha256_file(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def open_url(url: str) -> BinaryIO:  # pragma: no cover (network)
    request = Request(url, headers={"User-Agent": "holdsup-reranker-fetch"})  # noqa: S310 (https, fixed host)
    return cast(BinaryIO, urlopen(request, timeout=60))  # noqa: S310 (as above)


def fetch(pin_path: Path, dest: Path, opener: Opener = open_url) -> list[str]:
    """Put every pinned file in `dest`; one line per file saying what was done."""
    repo, revision, files = read_pin(pin_path)
    dest.mkdir(parents=True, exist_ok=True)
    done: list[str] = []
    for name, expected in sorted(files.items()):
        target = dest / name
        if target.exists():
            if sha256_file(target) != expected:
                raise FetchError(
                    f"{target} is there with another sha256 than the pin's; move it away "
                    "first (it may be a local retrain), or pin that export instead"
                )
            done.append(f"{name}: already there, sha256 ok")
            continue
        part = dest / f"{name}.part"
        digest = hashlib.sha256()
        try:
            with opener(file_url(repo, revision, name)) as response, part.open("wb") as out:
                while chunk := response.read(CHUNK):
                    digest.update(chunk)
                    out.write(chunk)
            if (got := digest.hexdigest()) != expected:
                raise FetchError(f"{name}: the download's sha256 is {got}, the pin says {expected}")
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        part.replace(target)
        done.append(f"{name}: downloaded from {repo}@{revision[:7]}, sha256 ok")
    return done


def main(argv: Sequence[str] | None = None, opener: Opener = open_url) -> int:
    parser = argparse.ArgumentParser(
        prog="fetch_reranker", description="Download the pinned reranker export, sha256-checked."
    )
    parser.add_argument("pin", type=Path, help="holdsup/ml/reranker_pin.json")
    parser.add_argument("dest", type=Path, help="the folder to put the export in")
    args = parser.parse_args(argv)
    try:
        lines = fetch(args.pin, args.dest, opener)
    except (FetchError, OSError) as exc:  # OSError: the Hub unreachable, an HTTP error
        print(f"fetch_reranker: {exc}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
