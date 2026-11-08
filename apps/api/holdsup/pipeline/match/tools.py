"""The tools the model may call while matching: one registry entry per tool.

Each entry holds what the model is told (description, parameters) and how code answers it.
`TOOLS`, what the router sends, derives from the registry, so adding a tool is one entry here
and a mention in the system prompt.
"""

import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from openai.types.chat import ChatCompletionToolUnionParam

from holdsup.catalog.schema import IndicatorSpec
from holdsup.pipeline.match.candidates import CandidatePool
from holdsup.pipeline.match.model import MatchRun, ToolUse
from holdsup.pipeline.match.prompt import describe
from holdsup.router.client import ToolCall

MAX_TOOL_CALLS = 4

ToolHandler = Callable[[CandidatePool, MatchRun, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class Tool:
    description: str
    parameters: dict[str, Any]
    run: ToolHandler


class _ToolError(Exception):
    """A call the tool cannot answer; the model reads the message as `{"error": ...}`."""


def _takes(name: str) -> dict[str, Any]:
    """JSON schema of a tool with one required string argument."""
    return {"type": "object", "properties": {name: {"type": "string"}}, "required": [name]}


def _entry(pool: CandidatePool, run: MatchRun, args: dict[str, Any]) -> tuple[IndicatorSpec, bool]:
    """The entry the call names and whether it covers the claim's place. An entry that does
    becomes one the model may pick."""
    indicator_id = str(args.get("indicator_id", ""))
    try:
        spec = pool.catalog.get(indicator_id)
    except KeyError as exc:
        raise _ToolError(f"unknown indicator_id {indicator_id!r}") from exc
    fits = pool.covers(spec, run.claim.geo)
    if fits:
        run.eligible.setdefault(spec.id, spec)
    return spec, fits


async def _search_catalog(
    pool: CandidatePool, run: MatchRun, args: dict[str, Any]
) -> dict[str, Any]:
    hits, _ = await pool.covering(str(args.get("query", "")), run.claim.geo)
    for h in hits:
        run.eligible.setdefault(h.id, pool.catalog.get(h.id))
    return {"results": [describe(pool.catalog.get(h.id))[2:] for h in hits]}


_META_FIELDS = {
    "id",
    "name",
    "definition",
    "unit",
    "frequency",
    "source",
    "first_year",
    "last_year",
    "geo_coverage",
    "related",
}


async def _indicator_meta(
    pool: CandidatePool, run: MatchRun, args: dict[str, Any]
) -> dict[str, Any]:
    spec, fits = _entry(pool, run, args)
    return {**spec.model_dump(mode="json", include=_META_FIELDS), "covers_claim_place": fits}


async def _list_geos(pool: CandidatePool, run: MatchRun, args: dict[str, Any]) -> dict[str, Any]:
    spec, fits = _entry(pool, run, args)
    return {"geo_coverage": spec.geo_coverage, "covers_claim_place": fits}


TOOL_REGISTRY: Mapping[str, Tool] = {
    "search_catalog": Tool(
        "Search the indicator catalog with another phrasing. Returns up to 8 entries that "
        "cover the claim's place.",
        _takes("query"),
        _search_catalog,
    ),
    "get_indicator_meta": Tool(
        "Full catalog entry: definition, unit, frequency, years, coverage and related entries.",
        _takes("indicator_id"),
        _indicator_meta,
    ),
    "list_geos": Tool(
        "The places an entry covers, and whether it covers the claim's.",
        _takes("indicator_id"),
        _list_geos,
    ),
}

TOOLS: list[ChatCompletionToolUnionParam] = [
    {
        "type": "function",
        "function": {"name": name, "description": tool.description, "parameters": tool.parameters},
    }
    for name, tool in TOOL_REGISTRY.items()
]


async def answer_tool_call(pool: CandidatePool, run: MatchRun, call: ToolCall) -> str:
    """Run one tool call and record it; the answer is JSON for the model. Calls past the
    budget, unknown tools and bad arguments get an error the model can read."""
    if len(run.tool_calls) >= MAX_TOOL_CALLS:
        run.tool_calls.append(ToolUse(name=call.name, arguments=call.arguments, ok=False))
        return json.dumps({"error": f"tool budget of {MAX_TOOL_CALLS} calls spent"})
    try:
        args = json.loads(call.arguments or "{}")
        if not isinstance(args, dict):
            raise TypeError
        tool = TOOL_REGISTRY.get(call.name)
        if tool is None:
            raise _ToolError(f"unknown tool {call.name!r}")
        out, ok = await tool.run(pool, run, args), True
    except (ValueError, TypeError):
        out, ok = {"error": "arguments must be a JSON object"}, False
    except _ToolError as exc:
        out, ok = {"error": str(exc)}, False
    run.tool_calls.append(ToolUse(name=call.name, arguments=call.arguments, ok=ok))
    return json.dumps(out, ensure_ascii=False)
