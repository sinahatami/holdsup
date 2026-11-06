"""Smoke-test every configured model provider through the router. Not part of CI.

Usage (from the repo root, with keys in .env):  make smoke-providers
Each provider gets two calls: a JSON-schema answer and a forced tool call. Exit code is 1 if
any provider with a key fails a check.
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolUnionParam
from pydantic import BaseModel

from holdsup.router import ProviderConfig, Router, RouterConfig, RouterError, Use
from holdsup.router.client import OpenAICompatibleClient, SupportsChat
from holdsup.router.config import Capability, load_router_config

STEP = "smoke"


class CapitalAnswer(BaseModel):
    country: str
    capital: str


SCHEMA_MESSAGES: list[ChatCompletionMessageParam] = [
    {"role": "system", "content": "Answer in JSON only."},
    {"role": "user", "content": "What is the capital of Italy? Give country and capital."},
]

TOOL_MESSAGES: list[ChatCompletionMessageParam] = [
    {"role": "user", "content": "Look up the catalog entry for youth unemployment."},
]

TOOLS: list[ChatCompletionToolUnionParam] = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search the indicator catalog.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    }
]


@dataclass
class Row:
    provider: str
    model: str
    use: str
    key: bool
    json_schema: str = "-"
    tools: str = "-"
    latency_ms: str = "-"
    note: str = ""
    failures: list[str] = field(default_factory=list)  # full, redacted provider errors

    @property
    def failed(self) -> bool:
        return self.key and ("FAIL" in (self.json_schema, self.tools))


def _single(config: RouterConfig, provider: ProviderConfig) -> RouterConfig:
    return RouterConfig(providers=(provider,), steps={STEP: (provider.name,)})


async def check_provider(
    config: RouterConfig, provider: ProviderConfig, client: SupportsChat
) -> Row:
    row = Row(provider.name, provider.model, provider.allowed_use.value, client.has_key(provider))
    if not row.key:
        row.note = f"{provider.api_key_env} not set"
        return row
    router = Router(_single(config, provider), client)
    notes: list[str] = []
    latencies: list[float] = []

    try:
        answer = await router.complete(STEP, SCHEMA_MESSAGES, use=Use.OFFLINE, schema=CapitalAnswer)
        ok = answer.parsed is not None and "rome" in answer.parsed.capital.lower()
        row.json_schema = "ok" if ok else "FAIL"
        if not ok:
            notes.append(f"schema: unexpected answer {answer.content!r}"[:120])
        if any(a.outcome == "malformed" for a in answer.attempts):
            notes.append("schema: needed a repair retry")
        latencies.append(answer.latency_ms)
    except RouterError as exc:
        row.json_schema = "FAIL"
        notes.append(f"schema: {_short(exc)}")
        row.failures.extend(f"schema: {d}" for d in exc.details or exc.attempts)

    if Capability.TOOLS not in provider.capabilities:
        row.tools = "n/a"
    else:
        try:
            called = await router.complete(
                STEP, TOOL_MESSAGES, use=Use.OFFLINE, tools=TOOLS, tool_choice="required"
            )
            calls = [c for c in called.tool_calls if c.name == "search_catalog"]
            valid = bool(calls) and _has_query(calls[0].arguments)
            row.tools = "ok" if valid else "FAIL"
            if not valid:
                notes.append(f"tools: no valid search_catalog call ({called.content!r})"[:120])
            latencies.append(called.latency_ms)
        except RouterError as exc:
            row.tools = "FAIL"
            notes.append(f"tools: {_short(exc)}")
            row.failures.extend(f"tools: {d}" for d in exc.details or exc.attempts)

    if latencies:
        row.latency_ms = f"{max(latencies):.0f}"
    row.note = "; ".join(notes)
    return row


def _short(exc: RouterError) -> str:
    """First failure, e.g. "rejected HTTP 404" (full text goes in the Failures section)."""
    if not exc.details:
        return ", ".join(exc.attempts) or "no attempt made"
    _, _, rest = exc.details[0].partition(" ")
    outcome, _, detail = rest.partition(": ")
    status = detail.split(":", 1)[0] if detail.startswith("HTTP") else ""
    return f"{outcome} {status}".strip()


def format_failures(rows: list[Row]) -> str:
    lines = [f"- {r.provider}: {f}" for r in rows for f in r.failures]
    return "\n".join(["", "Failures:", *lines]) if lines else ""


def _has_query(arguments: str) -> bool:
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, dict) and isinstance(parsed.get("query"), str)


def format_table(rows: list[Row]) -> str:
    headers = ["provider", "model", "use", "key", "json_schema", "tools", "max_ms", "note"]
    data = [
        [
            r.provider,
            r.model,
            r.use,
            "yes" if r.key else "no",
            r.json_schema,
            r.tools,
            r.latency_ms,
            r.note,
        ]
        for r in rows
    ]
    widths = [max(len(h), *(len(d[i]) for d in data)) for i, h in enumerate(headers)]
    line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    body = [
        "| " + " | ".join(c.ljust(w) for c, w in zip(d, widths, strict=True)) + " |" for d in data
    ]
    return "\n".join([line, sep, *body])


async def run(config: RouterConfig, client: SupportsChat) -> list[Row]:
    return [await check_provider(config, p, client) for p in config.providers]


def select(config: RouterConfig, only: list[str], model: str | None) -> RouterConfig:
    """Restrict to `only` providers; `model` overrides the model id of a single provider."""
    providers = [p for p in config.providers if not only or p.name in only]
    missing = set(only) - {p.name for p in providers}
    if missing:
        raise SystemExit(f"unknown provider(s): {sorted(missing)}")
    if model is not None:
        if len(providers) != 1:
            raise SystemExit("--model needs exactly one --only provider")
        providers = [providers[0].model_copy(update={"model": model})]
    return RouterConfig(providers=tuple(providers), steps={STEP: tuple(p.name for p in providers)})


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="make smoke-providers ARGS=...")
    parser.add_argument("--only", action="append", default=[], help="provider name (repeatable)")
    parser.add_argument("--model", help="try another model id for the single --only provider")
    args = parser.parse_args(argv)
    config = select(load_router_config(), args.only, args.model)
    rows = asyncio.run(run(config, OpenAICompatibleClient()))
    print(format_table(rows))
    if failures := format_failures(rows):
        print(failures)
    return 1 if any(r.failed for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
