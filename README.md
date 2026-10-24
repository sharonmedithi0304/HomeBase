# 🏡 HOMEBASE — THE HOUSEHOLD, FINALLY IN SYNC.

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&height=260&color=0:111827,35:312E81,70:7C3AED,100:06B6D4&text=HOMEBASE&fontColor=FFFFFF&fontSize=76&fontAlignY=40&desc=One%20household.%20One%20shared%20brain.&descSize=20&descAlignY=60&animation=fadeIn" width="100%" alt="HomeBase — One household, one shared brain"/>
</p>

<p align="center">
  <strong>YOUR FAMILY'S CHIEF OF STAFF FOR ALEXA+</strong>
  <br/>
  A self-hosted MCP server that turns household chaos into coordinated action.
  <br/><br/>
  <a href="https://github.com/sharonmedithi0304/HomeBase/stargazers"><img src="https://img.shields.io/github/stars/sharonmedithi0304/HomeBase?style=for-the-badge&logo=github&color=7C3AED&label=STARS" alt="GitHub stars"/></a>
  <a href="https://github.com/sharonmedithi0304/HomeBase/blob/main/LICENSE"><img src="https://img.shields.io/badge/LICENSE-MIT-06B6D4?style=for-the-badge" alt="MIT License"/></a>
  <img src="https://img.shields.io/badge/MCP-Streamable%20HTTP-8B5CF6?style=for-the-badge" alt="MCP Streamable HTTP"/>
  <img src="https://img.shields.io/badge/STATUS-OPEN%20SOURCE-10B981?style=for-the-badge" alt="Open source"/>
</p>

<p align="center">
  <a href="#-the-idea">THE IDEA</a> &nbsp;•&nbsp;
  <a href="#-the-experience">THE EXPERIENCE</a> &nbsp;•&nbsp;
  <a href="#-under-the-hood">THE ARCHITECTURE</a> &nbsp;•&nbsp;
  <a href="#-get-it-running">GET STARTED</a>
</p>

---

> **Your home doesn't need another list. It needs a system that helps everyone stay in sync.**

Who's handling pickup at 5:30? Who has been doing all the chores? Can that meeting fit into Arjun's schedule? Are we out of eggs again?

These aren't isolated reminders. They're connected decisions that affect an entire household.

**HomeBase brings those decisions together.** It gives Alexa+ a shared household context through an open-source, self-hosted Model Context Protocol (MCP) server, backed by practical scheduling, workload-aware chore assignment, rotating pickup coordination, grocery tracking, and a spoken daily briefing.

And because a system should be experienced, not merely described, HomeBase also includes an interactive smart-display simulator where you can talk to it, see the schedule, and watch its tools in action.

<p align="center">
  <img src="https://img.shields.io/badge/01-SHARED%20CONTEXT-312E81?style=flat-square" alt="Shared context"/>
  <img src="https://img.shields.io/badge/02-FAIRER%20CHORES-7C3AED?style=flat-square" alt="Fairer chores"/>
  <img src="https://img.shields.io/badge/03-SMARTER%20SCHEDULING-0891B2?style=flat-square" alt="Smarter scheduling"/>
  <img src="https://img.shields.io/badge/04-VOICE%20INTERACTION-0F766E?style=flat-square" alt="Voice interaction"/>
</p>

## ✦ The idea

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&height=3&color=0:7C3AED,50:06B6D4,100:10B981" width="100%" alt="Decorative gradient divider"/>
</p>

### A household is a team. Treat it like one.

HomeBase is designed around a simple principle: **good coordination means making decisions with the whole household in mind.**

| Everyday problem | What HomeBase does |
|---|---|
| Chores keep falling on the same person | Assigns chores based on workload |
| Pickup duty needs to be decided | Identifies eligible people and supports pickup assignment |
| Events clash on the calendar | Reports scheduling conflicts |
| Nobody remembers what's needed | Maintains a shared grocery list |
| Everyone asks what's happening today | Generates a daily briefing with a spoken response |
| A decision needs an explanation | Returns a `why` alongside relevant decisions |

The goal isn't to add more notifications to family life. It's to make the information and decisions behind everyday coordination accessible through one shared system.

## 🚀 The experience

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=soft&height=100&color=0:1E1B4B,100:164E63&text=LESS%20COORDINATION%20CHAOS&fontColor=FFFFFF&fontSize=25&animation=fadeIn" width="100%" alt="Less coordination chaos"/>
</p>

### 01 / A shared family brain

Keep household members, chores, schedules, pickup assignments, and groceries connected to a shared data layer.

Instead of treating every request as an isolated question, HomeBase provides tools that operate on the household's stored information.

### 02 / Chores with workload in mind

Household responsibilities should not automatically land on whoever remembers them first.

- Add chores and assign them based on workload.
- Mark completed chores.
- Check chore status.
- Make household responsibilities easier to track.

### 03 / Scheduling that catches clashes

Plans only work when they fit together.

- Add household events.
- Retrieve today's schedule.
- Detect and report scheduling conflicts.
- Identify who can handle a pickup.
- Assign pickup responsibilities.

### 04 / One grocery list for everyone

No more separate mental inventories.

- Add grocery items.
- View the shared list.
- Mark items as bought.

### 05 / A briefing you can hear

HomeBase can generate a daily briefing with a `spoken` response, giving a voice-enabled interface a ready-to-speak summary.

The smart-display simulator supports microphone input in compatible browsers, typed requests, suggestion prompts, and spoken replies.

### 06 / Decisions with a reason

A result is more useful when people understand why it was chosen.

HomeBase returns explanations with relevant decisions. For example, a pickup recommendation can explain that someone is available and has handled fewer pickups.

**Not just an answer. Context behind the answer.**

---

## 🖥️ Meet the smart-display simulator

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&height=125&color=0:0F172A,45:312E81,100:0891B2&text=THE%20HOMEBASE%20DISPLAY&fontColor=FFFFFF&fontSize=30&desc=See%20the%20tools.%20Follow%20the%20schedule.&descSize=15&descAlignY=72" width="100%" alt="HomeBase smart-display simulator"/>
</p>

The simulator is a local, interactive way to experience HomeBase without requiring an actual Alexa+ device.

Once the server is running, open:

**http://127.0.0.1:8000/**

Inside the simulator, you can:

- **Explore the timeline:** See one lane per household member.
- **Spot scheduling conflicts:** Double-bookings appear as hatched overlaps.
- **Follow pickup assignments:** Assigned rides appear as dashed bars.
- **Talk or type:** Use the microphone in a supported browser, enter a request, or tap a suggestion.
- **Hear responses:** Toggle spoken replies on or off.
- **Inspect tool calls:** See which MCP tool handled a request.

The simulator's `/api/tool` endpoint dispatches into the same `MCPServer` instance exposed through `/mcp`. That means the interface exercises the actual HomeBase tool implementations rather than a separate set of mock tool responses.

The sentence-to-tool mapping is handled by a small deterministic parser in `web/intents.js`, helping keep demonstrations predictable.

### Give it something to do

Try these example requests in the simulator:

| Say or type | What to explore |
|---|---|
| `What's the plan today?` | Daily schedule and briefing |
| `Assign the 5:30 pickup for Kabir from football` | Pickup coordination |
| `Add a chore: vacuum the stairs` | Chore creation and assignment |
| `Schedule school meeting for Arjun at 4 pm` | Event creation and conflict handling |
| `Add eggs to the grocery list` | Shared grocery tracking |
| `Who has the most chores?` | Household workload information |

*Exact results depend on the current household data and the simulator's supported intent patterns.*

---

## ⚡ Under the hood

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&height=100&color=0:312E81,50:6D28D9,100:0891B2&text=ONE%20SERVER.%20FOURTEEN%20TOOLS.&fontColor=FFFFFF&fontSize=26" width="100%" alt="One server, fourteen tools"/>
</p>

HomeBase exposes **14 MCP tools** across five household domains, alongside a summary resource.

| Domain | Tools | Purpose |
|---|---|---|
| Family | `add_family_member`, `list_family` | Manage household members |
| Chores | `add_chore`, `complete_chore`, `chore_status` | Create, assign, complete, and inspect chores |
| Schedule | `add_event`, `todays_schedule`, `who_can_pickup`, `assign_pickup` | Coordinate events and pickup duty |
| Groceries | `grocery_add`, `grocery_list`, `grocery_bought` | Manage the shared shopping list |
| Voice & demo | `daily_briefing`, `load_demo_family` | Generate briefings and load sample household data |

The server also exposes the `homebase://summary` resource.

### Built for understandable failures

Real systems need to handle invalid requests, not just successful demonstrations.

HomeBase raises readable MCP `ToolError` messages for anticipated problems, such as an unknown family member or an invalid time. This gives a voice interface useful feedback that can be communicated back to the user.

### The architecture

```mermaid
flowchart TD
    A["Alexa+ / MCP Client"] --> B["Streamable HTTP · /mcp"]
    C["HomeBase Smart Display"] --> D["Web Routes · /api/tool"]
    D --> E["Shared MCPServer Instance"]
    B --> E
    E --> F["HomeBase Core Logic"]
    F --> G[("Local SQLite Database")]
    E --> H["14 MCP Tools"]
    E --> I["homebase://summary"]
    C --> J["Intent Parser · web/intents.js"]
    J --> D
```

The separation keeps the core household logic distinct from the interface and protocol layer.

- `homebase/core.py` — household logic and SQLite persistence.
- `homebase/server.py` — MCP server and web routes.
- `web/` — smart-display interface and intent parsing.
- `scripts/` — scripted MCP client demonstration.
- `tests/` — Python and JavaScript tests.

## 🧰 Technology stack

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
  <img src="https://img.shields.io/badge/Model%20Context%20Protocol-7C3AED?style=for-the-badge" alt="Model Context Protocol"/>
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript"/>
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5"/>
  <img src="https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="pytest"/>
</p>

| Technology
