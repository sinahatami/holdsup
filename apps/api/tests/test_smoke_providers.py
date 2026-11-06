"""The smoke script's logic, with fake providers (the real run needs keys and network)."""

import json

import pytest
from scripts.smoke_providers import Row, format_failures, format_table, run, select

from holdsup.router.client import ChatResponse, ToolCall
from holdsup.router.errors import ProviderRejected
from tests.router.fakes import FakeClient, config, provider

GOOD_JSON = ChatResponse(content=json.dumps({"country": "Italy", "capital": "Rome"}))
GOOD_TOOL = ChatResponse(
    content=None,
    tool_calls=(ToolCall(id="1", name="search_catalog", arguments='{"query": "youth"}'),),
)


async def test_smoke_rows_and_table() -> None:
    cfg = config(
        provider("good"),
        provider("bad-key"),
        provider("no-tools", capabilities=("json_object",)),
        provider("broken"),
        provider("nokey"),
    )
    client = FakeClient(keys={"good", "bad-key", "no-tools", "broken"})
    client.script("good", [GOOD_JSON, GOOD_TOOL])
    client.script("bad-key", [ProviderRejected("HTTP 401"), ProviderRejected("HTTP 401")])
    client.script("no-tools", [GOOD_JSON])
    client.script(
        "broken",
        [
            ChatResponse(content="Rome!"),
            ChatResponse(content=json.dumps({"country": "Italy", "capital": "Paris"})),
            ChatResponse(content="I would search the catalog."),
        ],
    )

    rows = {r.provider: r for r in await run(cfg, client)}

    assert (rows["good"].json_schema, rows["good"].tools, rows["good"].failed) == (
        "ok",
        "ok",
        False,
    )
    assert rows["bad-key"].json_schema == "FAIL" and rows["bad-key"].failed
    assert "rejected" in rows["bad-key"].note
    assert (rows["no-tools"].json_schema, rows["no-tools"].tools) == ("ok", "n/a")
    assert rows["broken"].json_schema == "FAIL"
    assert "repair retry" in rows["broken"].note
    assert rows["broken"].tools == "FAIL"
    assert (rows["nokey"].key, rows["nokey"].failed) == (False, False)
    assert "NOKEY_KEY not set" in rows["nokey"].note

    table = format_table(list(rows.values())).splitlines()
    assert table[0].startswith("| provider")
    assert len(table) == 2 + 5
    assert len({len(line) for line in table}) == 1  # aligned columns

    # Tool call used tool_choice="required" and the tools list.
    tool_request = client.calls[1][1]
    assert tool_request.tool_choice == "required"
    assert tool_request.tools is not None


def test_failures_section_and_short_note() -> None:

    row = Row("p", "m", "live", True, failures=["schema: p rejected: HTTP 404: gone"])
    assert format_failures([row]) == "\nFailures:\n- p: schema: p rejected: HTTP 404: gone"
    assert format_failures([Row("q", "m", "live", False)]) == ""


async def test_failure_note_shows_status() -> None:
    cfg = config(provider("gone"))
    client = FakeClient()
    client.script("gone", [ProviderRejected("HTTP 404: no such model")] * 2)
    [row] = await run(cfg, client)
    assert row.note == "schema: rejected HTTP 404; tools: rejected HTTP 404"
    assert row.failures == [
        "schema: gone rejected: HTTP 404: no such model",
        "tools: gone rejected: HTTP 404: no such model",
    ]


def test_select_only_and_model_override() -> None:

    cfg = config(provider("a"), provider("b"))
    only_b = select(cfg, ["b"], "other-model")
    assert [(p.name, p.model) for p in only_b.providers] == [("b", "other-model")]
    assert len(select(cfg, [], None).providers) == 2
    with pytest.raises(SystemExit, match="unknown"):
        select(cfg, ["zzz"], None)
    with pytest.raises(SystemExit, match="exactly one"):
        select(cfg, [], "m")
