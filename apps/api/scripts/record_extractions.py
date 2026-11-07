"""Record real extraction responses for the P2.1 unit tests (tests never call a model).

Usage (from the repo root, with keys in .env):  make record-extractions [ARGS="e01 e07"]
Reads tests/fixtures/extract/cases.json, runs each case's text through the live router's
`extract` step and saves the raw response under `recorded`. Hand-written `expected` blocks
are kept. With ids, only those cases are re-recorded.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from holdsup.pipeline.extract import extract_claims
from holdsup.router import Router, RouterError, Use, load_router_config
from holdsup.router.client import OpenAICompatibleClient

CASES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "extract" / "cases.json"


async def record(cases: list[dict[str, Any]], only: set[str]) -> int:
    router = Router(load_router_config(), OpenAICompatibleClient())
    failed = 0
    for case in cases:
        if only and case["id"] not in only:
            continue
        try:
            result = await extract_claims(
                router, case["text"], use=Use.LIVE, said_on=case.get("said_on")
            )
        except RouterError as exc:
            print(f"{case['id']}: {exc}", file=sys.stderr)
            failed += 1
            continue
        case["recorded"] = {
            "provider": result.provider,
            "model": result.model,
            "content": result.content,
        }
        print(f"{case['id']}: {result.provider}, {len(result.claims)} claim(s)", file=sys.stderr)
    return failed


def main(argv: list[str]) -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    failed = asyncio.run(record(cases, set(argv)))
    CASES.write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {CASES}" + (f" ({failed} failed)" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
