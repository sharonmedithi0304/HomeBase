import asyncio
import json
from datetime import date

import pytest

from homebase import core, server
from mcp.server.mcpserver.exceptions import ToolError

TODAY = date.today().isoformat()


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB_PATH", str(tmp_path / "srv.db"))


def call(name, **args):
    res = asyncio.run(server.mcp.call_tool(name, args))
    return json.loads("".join(b.text for b in res.content))


def test_fourteen_tools_registered():
    tools = asyncio.run(server.mcp.list_tools())
    assert len(tools) == 14


def test_tool_flow_through_mcp_layer():
    call("load_demo_family")
    r = call("assign_pickup", title="Pick up Kabir", start=f"{TODAY}T17:30", end=f"{TODAY}T18:15")
    assert r["member"] in ("Maya", "Arjun") and "fewest pickups" in r["why"]


def test_friendly_errors_reach_mcp_clients():
    call("load_demo_family")
    with pytest.raises(ToolError, match="Known members"):
        call("add_event", title="x", member="Nobody", start=f"{TODAY}T10:00", end=f"{TODAY}T11:00")


def test_web_api_routes():
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient

    client = TestClient(server.mcp.streamable_http_app())
    assert client.get("/").status_code == 200
    assert "parseIntent" in client.get("/intents.js").text
    assert client.post("/api/reset").json()["ok"] is True
    state = client.get("/api/state").json()
    assert len(state["family"]) == 4 and state["events"]

    ok = client.post("/api/tool", json={"name": "grocery_add", "arguments": {"item": "Eggs"}}).json()
    assert ok["ok"] and ok["data"]["note"] == "added"

    bad = client.post("/api/tool", json={"name": "add_event",
                                         "arguments": {"title": "x", "member": "Nobody",
                                                       "start": f"{TODAY}T10:00", "end": f"{TODAY}T11:00"}}).json()
    assert bad["ok"] is False and "Known members" in bad["error"]

    unknown = client.post("/api/tool", json={"name": "rm_rf", "arguments": {}})
    assert unknown.status_code == 404
