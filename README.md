# HomeBase: your family's chief of staff for Alexa+

A self-hosted **MCP server** (Streamable HTTP, protocol 2026-07-28, newer than the 2025-11-25 minimum)
that gives Alexa+ a shared brain for the household: fair chores, a schedule that catches clashes,
pickup duty that rotates, a grocery list, and a spoken morning briefing. It ships with a
**simulated Alexa+ smart display** (voice in, voice out) so you can see and hear it work.

**Track:** Alexa+  **Mini challenge:** Open Source (MIT)

## Why it's useful
Families don't need another calendar. They need the *decisions* made: who takes the 5:30 pickup, whose turn
it is for the heavy chore, and "wait, Arjun is double-booked". HomeBase returns a `why` with every decision so
Alexa+ can say it out loud ("Maya is free and has done the fewest pickups").

## The MCP server (14 tools)
| Area | Tools |
|---|---|
| Family | `add_family_member`, `list_family` |
| Chores | `add_chore` (auto-assigns by workload), `complete_chore`, `chore_status` |
| Schedule | `add_event` (reports conflicts), `todays_schedule`, `who_can_pickup`, `assign_pickup` |
| Grocery | `grocery_add`, `grocery_list`, `grocery_bought` |
| Voice | `daily_briefing` (returns a `spoken` string), `load_demo_family` |

Plus the resource `homebase://summary`. Anticipated failures (unknown family member, bad time) are raised as
MCP `ToolError`s with a readable message, so Alexa+ can tell the user what to fix.

## The smart-display simulator
Open `http://127.0.0.1:8000/` while the server runs.

- Timeline with one lane per person; double-bookings show as hatched overlaps, assigned rides as dashed bars.
- Talk to it with the mic (Chrome or Edge), type, or tap a suggestion. Toggle "Speak replies" to hear answers.
- Every reply shows which MCP tool it called. The page's `/api/tool` endpoint dispatches into the same
  `MCPServer` instance that Alexa+ would reach at `/mcp`, so the simulator exercises the real tools.
- The sentence-to-tool step is a small deterministic parser (`web/intents.js`), so demos behave the same every take.

Try: "What's the plan today?", "Assign the 5:30 pickup for Kabir from football", "Add a chore: vacuum the stairs",
"Schedule school meeting for Arjun at 4 pm", "Add eggs to the grocery list", "Who has the most chores?"

## Quick start
```bash
pip install -r requirements.txt
python -m homebase.server --port 8000      # MCP at http://127.0.0.1:8000/mcp, UI at http://127.0.0.1:8000/
python scripts/demo_client.py              # second terminal: scripted MCP-client demo over Streamable HTTP
python -m pytest -q tests                  # Python tests
node web/intents.test.js                   # parser tests (needs Node, optional)
```
Data lives in a local SQLite file (`HOMEBASE_DB` to relocate). `--stdio` is also supported for local MCP clients.
"Reset demo" in the UI (or saying "reset") restores the sample family for clean retakes.

## Connecting to Alexa+
Expose the server over HTTPS (for example `cloudflared tunnel --url http://localhost:8000`, or deploy to any
container host) and register the `/mcp` URL as your MCP integration in the Alexa+ developer preview.

## Layout
- `homebase/core.py`: pure logic and SQLite, unit-tested
- `homebase/server.py`: MCP tools (`MCPServer` from the official `mcp` SDK) plus the web routes
- `web/index.html`, `web/intents.js`: the smart-display simulator
- `scripts/demo_client.py`: end-to-end MCP client over Streamable HTTP
- `tests/`: pytest suite

## Hackathon notes
Built during the Amazon Developer Hackathon window (Oct 2026). All code in this repo was written for it.

## License
MIT
