# /// script
# requires-python = ">=3.13"
# dependencies = ["fonttools[woff]==4.68.0"]
# ///
"""Cut Newsreader down to what the site sets, for next/font/local (D038).

Usage (from the repository root):  make fonts

Google Fonts serves both Newsreader styles with every weight (200-800) and every optical size
(6-72), and that variation data is most of each file: 132 KB for the roman and 147 KB for the
italic, both preloaded on every page. The site sets the roman at 400 and 500, never below
17 px, and the italic only in the home title (400, 44-68 px). So this writes:

  newsreader-latin.woff2         roman, Latin, wght 400-500, opsz 16-72   preloaded
  newsreader-latin-ext.woff2     roman, Latin Extended + Vietnamese, same axes
                                 (downloaded only by a page with such a letter)
  newsreader-italic-latin.woff2  italic, Latin, wght 400, opsz 44-72      preloaded

Below or above an axis range the browser clamps to its end, so the cut changes nothing at the
sizes the site uses. A new weight, a smaller size or the italic somewhere else needs a wider
range here, `make fonts`, and the matching `weight` in apps/web/src/app/layout.tsx.

The sources are pinned to a google/fonts commit, checked by sha256, and downloaded once into
.cache/fonts. The Latin ranges are Google Fonts' own subsets, so coverage is what it was.
"""

import hashlib
import io
import shutil
import sys
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "fonts"
OUT = ROOT / "apps" / "web" / "src" / "app" / "fonts"
LAYOUT = ROOT / "apps" / "web" / "src" / "app" / "layout.tsx"

COMMIT = "8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5"  # google/fonts, ofl/newsreader, Version 1.003
BASE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl/newsreader"
SOURCES = {
    "Newsreader[opsz,wght].ttf": (
        "8a08d13f8a6c0d51be379a60af84f945f65369a67e509ee3c3bdcc421254d7c1"
    ),
    "Newsreader-Italic[opsz,wght].ttf": (
        "796668611f80b64d5adf182fde3b6f29ed83b4e7cbec7b96937e84ac01364792"
    ),
    "OFL.txt": "fdfad38143ec470553cae82a1e45320bdd1b9ec70415d37bd0171051d8a4ded8",
}

# Google Fonts' unicode ranges for its "latin", "latin-ext" and "vietnamese" subsets.
LATIN = (
    "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, "
    "U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"
)
LATIN_EXT = (
    "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, "
    "U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, "
    "U+2C60-2C7F, U+A720-A7FF"
)
VIETNAMESE = (
    "U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, U+01AF-01B0, "
    "U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, U+20AB"
)
# The extra file's range; layout.tsx declares it as the face's unicode-range.
EXTRA = f"{LATIN_EXT}, {VIETNAMESE}"

Limits = dict[str, float | tuple[float, float]]
ROMAN: Limits = {"wght": (400, 500), "opsz": (16, 72)}
ITALIC: Limits = {"wght": 400, "opsz": (44, 72)}

# output name -> (source, unicode range, axis limits)
CUTS: dict[str, tuple[str, str, Limits]] = {
    "newsreader-latin.woff2": ("Newsreader[opsz,wght].ttf", LATIN, ROMAN),
    "newsreader-latin-ext.woff2": ("Newsreader[opsz,wght].ttf", EXTRA, ROMAN),
    "newsreader-italic-latin.woff2": ("Newsreader-Italic[opsz,wght].ttf", LATIN, ITALIC),
}


def codepoints(ranges: str) -> set[int]:
    out: set[int] = set()
    for part in ranges.split(","):
        first, _, last = part.strip().removeprefix("U+").partition("-")
        out.update(range(int(first, 16), int(last or first, 16) + 1))
    return out


def source(name: str) -> Path:
    """The pinned source file, downloaded once and checked by sha256."""
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        url = f"{BASE}/{urllib.request.quote(name)}"
        # A fixed https address on raw.githubusercontent.com, pinned to a commit.
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
            path.write_bytes(response.read())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SOURCES[name]:
        path.unlink()
        sys.exit(f"{name}: sha256 {digest} is not the pinned {SOURCES[name]}; removed it")
    return path


def cut(src: Path, ranges: str, limits: Limits) -> bytes:
    font = instancer.instantiateVariableFont(TTFont(src), limits)
    options = subset.Options()
    options.layout_features = ["*"]  # keep every OpenType feature (figures, ligatures)
    options.name_IDs = ["*"]  # keep the copyright and licence records
    options.hinting = False  # as Google Fonts serves it to browsers
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=codepoints(ranges))
    subsetter.subset(font)
    font.flavor = "woff2"
    buffer = io.BytesIO()
    font.save(buffer)
    return buffer.getvalue()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (src, ranges, limits) in CUTS.items():
        data = cut(source(src), ranges, limits)
        (OUT / name).write_bytes(data)
        print(f"{name:32} {len(data) / 1000:6.1f} KB")
    shutil.copyfile(source("OFL.txt"), OUT / "OFL-Newsreader.txt")
    if EXTRA not in LAYOUT.read_text(encoding="utf-8"):
        sys.exit(f"layout.tsx must declare this unicode-range for the extra file:\n{EXTRA}")


if __name__ == "__main__":
    main()
