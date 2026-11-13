"""scripts/fetch_reranker.py with a fake opener: what it downloads, keeps and refuses."""

import hashlib
import io
import json
from pathlib import Path
from typing import BinaryIO

import pytest
from scripts.fetch_reranker import FetchError, fetch, file_url, main

REVISION = "0123456789abcdef0123456789abcdef01234567"
FILES = {"model.onnx": b"onnx bytes", "tokenizer.json": b"{}", "reranker.json": b"[]"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_pin(folder: Path, files: dict[str, bytes] = FILES, revision: str = REVISION) -> Path:
    path = folder / "pin.json"
    pin = {
        "repo": "someone/model",
        "revision": revision,
        "files": {n: digest(d) for n, d in files.items()},
    }
    path.write_text(json.dumps(pin))
    return path


class Hub:
    """Serves `files` by URL and records what was asked for."""

    def __init__(self, files: dict[str, bytes] = FILES) -> None:
        self.files = files
        self.urls: list[str] = []

    def __call__(self, url: str) -> BinaryIO:
        self.urls.append(url)
        return io.BytesIO(self.files[url.rsplit("/", 1)[1]])


def test_every_file_is_downloaded_from_the_pinned_commit(tmp_path: Path) -> None:
    hub = Hub()
    lines = fetch(write_pin(tmp_path), tmp_path / "out", hub)

    assert sorted(hub.urls) == sorted(
        f"https://huggingface.co/someone/model/resolve/{REVISION}/{name}" for name in FILES
    )
    assert {p.name: p.read_bytes() for p in (tmp_path / "out").iterdir()} == FILES
    assert all("downloaded from someone/model@0123456, sha256 ok" in line for line in lines)


def test_files_already_there_are_kept(tmp_path: Path) -> None:
    pin = write_pin(tmp_path)
    fetch(pin, tmp_path / "out", Hub())
    hub = Hub()
    lines = fetch(pin, tmp_path / "out", hub)
    assert hub.urls == [] and all("already there" in line for line in lines)


def test_a_different_local_file_is_never_overwritten(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "model.onnx").write_bytes(b"a local retrain")
    with pytest.raises(FetchError, match="another sha256"):
        fetch(write_pin(tmp_path), out, Hub())
    assert (out / "model.onnx").read_bytes() == b"a local retrain"


def test_a_download_that_does_not_match_leaves_nothing(tmp_path: Path) -> None:
    pin = write_pin(tmp_path)
    tampered = {**FILES, "model.onnx": b"other bytes"}
    with pytest.raises(FetchError, match="model.onnx: the download's sha256"):
        fetch(pin, tmp_path / "out", Hub(tampered))
    assert not (tmp_path / "out" / "model.onnx").exists()
    assert not (tmp_path / "out" / "model.onnx.part").exists()


def test_a_branch_name_is_not_a_revision(tmp_path: Path) -> None:
    with pytest.raises(FetchError, match="40-hex commit hash"):
        fetch(write_pin(tmp_path, revision="main"), tmp_path / "out", Hub())


def test_an_unreachable_hub_leaves_no_partial_file(tmp_path: Path) -> None:
    def down(url: str) -> BinaryIO:
        raise OSError("connection refused")

    out = tmp_path / "out"
    assert main([str(write_pin(tmp_path)), str(out)], down) == 1
    assert list(out.iterdir()) == []


def test_main_reports_each_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(write_pin(tmp_path)), str(tmp_path / "out")], Hub()) == 0
    assert capsys.readouterr().out.count("sha256 ok") == 3


def test_main_explains_a_refusal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(write_pin(tmp_path, revision="main")), str(tmp_path / "out")], Hub()) == 1
    assert capsys.readouterr().err.startswith("fetch_reranker: ")


def test_the_committed_pin_reads_as_the_api_reads_it() -> None:
    from scripts.fetch_reranker import read_pin

    from holdsup.ml.reranker import PIN_FILE, load_pin

    repo, revision, files = read_pin(PIN_FILE)
    pin = load_pin()
    assert (repo, revision, files) == (pin.repo, pin.revision, pin.files)
    assert file_url(repo, revision, "model.onnx") == (
        f"https://huggingface.co/{pin.repo}/resolve/{pin.revision}/model.onnx"
    )
