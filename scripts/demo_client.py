"""Scripted end-to-end demo against a running HomeBase server over Streamable HTTP.

    python scripts/demo_client.py [http://127.0.0.1:8000/mcp]

Doubles as the smoke test and as the screen-recording script for the demo video.
"""
import asyncio
import json
import sys
from datetime import date

from mcp.client.client import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
TODAY = date.today().isoformat()


def text(result) -> str:
    return "".join(getattr(b, "text", "") for b in result.content)


async def say(client, label, tool, **args):
    print(f"\n\033[1;36m> {label}\033[0m  [{tool}]")
    res = await client.call_tool(tool, args)
    out = text(res)
    try:
        data = json.loads(out)
        if isinstance(data, dict) and "spoken" in data:
            print(f"\033[1;32mAlexa+:\033[0m {data['spoken']}")
        else:
            print(json.dumps(data, indent=2)[:900])
    except json.JSONDecodeError:
        print(out)
    return out


async def main():
    async with Client(URL) as client:
        tools = await client.list_tools()
        print(f"Connected. protocol={client.protocol_version}  tools={len(tools.tools)}")
        await say(client, "Alexa, load the demo family", "load_demo_family")
        await say(client, "What's the plan today?", "daily_briefing")
        await say(client, "Who can pick up the kids at 5:30?", "who_can_pickup",
                  start=f"{TODAY}T17:30", end=f"{TODAY}T18:15")
        await say(client, "Assign the 5:30 pickup", "assign_pickup",
                  title="Pick up Kabir from football", start=f"{TODAY}T17:30", end=f"{TODAY}T18:15")
        await say(client, "Add a chore, you decide who", "add_chore", title="Vacuum the stairs", effort=3)
        await say(client, "Dentist overlaps? Add a clash", "add_event", title="School meeting",
                  member="Arjun", start=f"{TODAY}T16:00", end=f"{TODAY}T17:00")
        await say(client, "Add eggs to the list", "grocery_add", item="Eggs", qty="12", added_by="Riya")
        await say(client, "Mark laundry done", "complete_chore", title="Laundry")
        await say(client, "Fairness check", "chore_status")
        await say(client, "Final briefing", "daily_briefing")


asyncio.run(main())
