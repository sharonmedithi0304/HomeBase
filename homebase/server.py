"""HomeBase MCP server (Streamable HTTP) for Alexa+.

Run:  python -m homebase.server            -> http://127.0.0.1:8000/mcp
"""
from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from . import core

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

mcp = MCPServer(
    name="HomeBase",
    title="HomeBase: your family's chief of staff",
    instructions=(
        "HomeBase coordinates a household: members, fair chore assignment, a shared schedule "
        "with conflict detection, pickup duty, a grocery list and a spoken daily briefing. "
        "Replies are short and voice-friendly; read the `spoken` or `why` fields aloud when present. "
        "If a tool returns an error, tell the user plainly what is missing and offer the fix."
    ),
)


@contextmanager
def db():
    conn = core.connect()
    try:
        yield conn
    except ValueError as e:
        # Anticipated, user-fixable problems (unknown member, bad time, ...) become
        # ToolErrors so MCP clients such as Alexa+ get the readable message.
        raise ToolError(str(e)) from e
    finally:
        conn.close()


def _ok(payload) -> str:
    return json.dumps(payload, indent=2, default=str)


# ------------------------------------------------------------------- members
@mcp.tool()
def add_family_member(name: str, role: str = "adult", can_drive: bool | None = None) -> str:
    """Add someone to the household. role is adult, teen or kid. Adults can drive by default."""
    with db() as c:
        return _ok(core.add_member(c, name, role, can_drive))


@mcp.tool()
def list_family() -> str:
    """List everyone in the household with their role and whether they can drive."""
    with db() as c:
        return _ok(core.list_members(c))


# -------------------------------------------------------------------- chores
@mcp.tool()
def add_chore(title: str, effort: int = 2, assignee: str | None = None, due: str | None = None) -> str:
    """Create a chore. effort is 1 (easy) to 5 (hard). If no assignee is given, HomeBase picks the
    fairest person based on open and recently completed workload and explains why. due is YYYY-MM-DD."""
    with db() as c:
        return _ok(core.add_chore(c, title, effort, assignee, due))


@mcp.tool()
def complete_chore(chore_id: int | None = None, title: str | None = None) -> str:
    """Mark a chore done, by id or by part of its title (e.g. 'laundry')."""
    with db() as c:
        return _ok(core.complete_chore(c, chore_id, title))


@mcp.tool()
def chore_status() -> str:
    """Open chores (with overdue flags) plus a fairness view of each person's workload."""
    with db() as c:
        return _ok(core.chore_status(c))


# ------------------------------------------------------------------ schedule
@mcp.tool()
def add_event(title: str, member: str, start: str, end: str) -> str:
    """Add a calendar event for a member. start/end are ISO datetimes like 2026-10-20T16:30.
    The reply lists any conflicts with that member's existing events."""
    with db() as c:
        return _ok(core.add_event(c, title, member, start, end))


@mcp.tool()
def todays_schedule(day: str | None = None) -> str:
    """Everyone's events for a day (YYYY-MM-DD, default today), plus double-booking conflicts."""
    from datetime import date
    day = day or date.today().isoformat()
    with db() as c:
        return _ok({"date": day, "events": core.events_on(c, day), "conflicts": core.find_conflicts(c, day)})


@mcp.tool()
def who_can_pickup(start: str, end: str) -> str:
    """Which drivers are free in a time window, fewest past pickups first."""
    with db() as c:
        return _ok(core.who_can_pickup(c, start, end))


@mcp.tool()
def assign_pickup(title: str, start: str, end: str) -> str:
    """Fairly assign a pickup/drop-off to a free driver and put it on their calendar."""
    with db() as c:
        return _ok(core.assign_pickup(c, title, start, end))


# ------------------------------------------------------------------- grocery
@mcp.tool()
def grocery_add(item: str, qty: str = "1", added_by: str | None = None) -> str:
    """Add an item to the shared grocery list (no duplicates)."""
    with db() as c:
        return _ok(core.grocery_add(c, item, qty, added_by))


@mcp.tool()
def grocery_list() -> str:
    """Read out what is still on the grocery list."""
    with db() as c:
        return _ok(core.grocery_list(c))


@mcp.tool()
def grocery_bought(item: str) -> str:
    """Check an item off the grocery list."""
    with db() as c:
        return _ok(core.grocery_bought(c, item))


# ------------------------------------------------------------------ briefing
@mcp.tool()
def daily_briefing(day: str | None = None) -> str:
    """A short, spoken-style briefing: events, conflicts, pickups, chores due, grocery count."""
    with db() as c:
        return _ok(core.daily_briefing(c, day))


@mcp.tool()
def load_demo_family() -> str:
    """Seed a sample family (Maya, Arjun, Riya, Kabir) with events, chores and groceries for demos.
    Does nothing if a family already exists."""
    with db() as c:
        return _ok(core.seed_demo(c))


@mcp.resource("homebase://summary")
def summary() -> str:
    """At-a-glance household summary."""
    with db() as c:
        return _ok({"family": core.list_members(c), "chores": core.chore_status(c),
                    "groceries": core.grocery_list(c)})


# ------------------------------------------------------- smart-display web UI
# The page below is a simulated Alexa+ smart display. Every action it takes goes
# through /api/tool, which dispatches into the same MCP tools Alexa+ would call.
@mcp.custom_route("/", methods=["GET"])
async def web_index(request: Request) -> HTMLResponse:
    return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))


@mcp.custom_route("/intents.js", methods=["GET"])
async def web_intents(request: Request) -> Response:
    return Response((WEB_DIR / "intents.js").read_text(encoding="utf-8"),
                    media_type="application/javascript")


@mcp.custom_route("/api/state", methods=["GET"])
async def web_state(request: Request) -> JSONResponse:
    day = request.query_params.get("day") or date.today().isoformat()
    with db() as c:
        brief = core.daily_briefing(c, day)
        return JSONResponse({
            "date": day,
            "family": core.list_members(c),
            "events": core.events_on(c, day),
            "conflicts": core.find_conflicts(c, day),
            "chores": core.chore_status(c),
            "grocery": core.grocery_list(c),
            "spoken": brief["spoken"],
        })


@mcp.custom_route("/api/tool", methods=["POST"])
async def web_tool(request: Request) -> JSONResponse:
    body = await request.json()
    name, args = body.get("name", ""), body.get("arguments") or {}
    known = {t.name for t in await mcp.list_tools()}
    if name not in known:
        return JSONResponse({"ok": False, "error": f"Unknown tool '{name}'."}, status_code=404)
    try:
        result = await mcp.call_tool(name, args)
    except UnexpectedToolError:
        return JSONResponse({"ok": False, "error": "Something went wrong inside HomeBase. Check the server window."})
    except ToolError as e:
        msg = str(e)
        prefix = f"Error executing tool {name}: "
        return JSONResponse({"ok": False, "error": msg[len(prefix):] if msg.startswith(prefix) else msg})
    text = "".join(getattr(b, "text", "") for b in result.content)
    if getattr(result, "is_error", False):
        return JSONResponse({"ok": False, "error": text})
    try:
        return JSONResponse({"ok": True, "tool": name, "data": json.loads(text)})
    except json.JSONDecodeError:
        return JSONResponse({"ok": True, "tool": name, "data": text})


@mcp.custom_route("/api/reset", methods=["POST"])
async def web_reset(request: Request) -> JSONResponse:
    with db() as c:
        core.reset_all(c)
        return JSONResponse({"ok": True, "data": core.seed_demo(c)})


def main() -> None:
    p = argparse.ArgumentParser(description="HomeBase MCP server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--stdio", action="store_true", help="use stdio instead of Streamable HTTP")
    a = p.parse_args()
    if a.stdio:
        mcp.run("stdio")
        return
    import uvicorn
    uvicorn.run(mcp.streamable_http_app(), host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()
