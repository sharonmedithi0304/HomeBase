"""HomeBase core logic: a tiny SQLite-backed family coordination engine.

Pure functions, no MCP imports, so everything is unit-testable and the MCP
layer in server.py stays a thin wrapper.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = os.environ.get("HOMEBASE_DB", str(Path(__file__).parent.parent / "homebase.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL COLLATE NOCASE,
  role TEXT NOT NULL DEFAULT 'adult',      -- adult | teen | kid
  can_drive INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS chores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  effort INTEGER NOT NULL DEFAULT 2,       -- 1 (easy) .. 5 (hard)
  assignee_id INTEGER REFERENCES members(id),
  due TEXT,                                -- YYYY-MM-DD
  done INTEGER NOT NULL DEFAULT 0,
  done_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  member_id INTEGER NOT NULL REFERENCES members(id),
  start TEXT NOT NULL,                     -- ISO datetime
  end TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'event'       -- event | pickup
);
CREATE TABLE IF NOT EXISTS grocery (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item TEXT NOT NULL COLLATE NOCASE,
  qty TEXT NOT NULL DEFAULT '1',
  added_by TEXT,
  bought INTEGER NOT NULL DEFAULT 0
);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


# --------------------------------------------------------------------- helpers
def _dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"'{s}' is not an ISO datetime like 2026-10-20T16:30") from e


def _member(conn, name: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM members WHERE name = ?", (name.strip(),)).fetchone()
    if not row:
        known = ", ".join(r["name"] for r in conn.execute("SELECT name FROM members")) or "nobody yet"
        raise ValueError(f"No family member called '{name}'. Known members: {known}.")
    return row


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


# --------------------------------------------------------------------- members
def add_member(conn, name: str, role: str = "adult", can_drive: bool | None = None) -> dict:
    role = role.lower()
    if role not in ("adult", "teen", "kid"):
        raise ValueError("role must be adult, teen or kid")
    if can_drive is None:
        can_drive = role == "adult"
    try:
        conn.execute("INSERT INTO members(name, role, can_drive) VALUES (?,?,?)",
                     (name.strip(), role, int(can_drive)))
    except sqlite3.IntegrityError:
        raise ValueError(f"{name} is already in the family.")
    conn.commit()
    return {"name": name.strip(), "role": role, "can_drive": bool(can_drive)}


def list_members(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT name, role, can_drive FROM members ORDER BY id")]


# ---------------------------------------------------------------------- chores
def _load(conn, member_id: int) -> int:
    """Open chore effort load for a member."""
    return conn.execute(
        "SELECT COALESCE(SUM(effort),0) FROM chores WHERE assignee_id=? AND done=0", (member_id,)
    ).fetchone()[0]


def _recent_done_load(conn, member_id: int, days: int = 14) -> int:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    return conn.execute(
        "SELECT COALESCE(SUM(effort),0) FROM chores WHERE assignee_id=? AND done=1 AND done_at>=?",
        (member_id, since),
    ).fetchone()[0]


def add_chore(conn, title: str, effort: int = 2, assignee: str | None = None,
              due: str | None = None) -> dict:
    if not 1 <= effort <= 5:
        raise ValueError("effort must be between 1 and 5")
    if due:
        date.fromisoformat(due)
    chosen, reason = None, None
    if assignee:
        chosen = _member(conn, assignee)
        reason = "assigned as requested"
    else:
        members = conn.execute(
            "SELECT * FROM members WHERE role != 'kid' OR ? <= 3", (effort,)
        ).fetchall()
        if not members:
            raise ValueError("Add family members first.")
        # fairness: lowest (open load + 14-day completed load); ties -> fewest open chores
        scored = sorted(
            members,
            key=lambda m: (_load(conn, m["id"]) + _recent_done_load(conn, m["id"]), m["id"]),
        )
        chosen = scored[0]
        reason = (f"{chosen['name']} has the lightest recent workload "
                  f"({_load(conn, chosen['id']) + _recent_done_load(conn, chosen['id'])} effort points)")
    cur = conn.execute(
        "INSERT INTO chores(title, effort, assignee_id, due) VALUES (?,?,?,?)",
        (title.strip(), effort, chosen["id"], due),
    )
    conn.commit()
    return {"id": cur.lastrowid, "title": title.strip(), "effort": effort,
            "assignee": chosen["name"], "due": due, "why": reason}


def complete_chore(conn, chore_id: int | None = None, title: str | None = None) -> dict:
    if chore_id is None and not title:
        raise ValueError("Give a chore id or part of its title.")
    if chore_id is not None:
        row = conn.execute("SELECT * FROM chores WHERE id=?", (chore_id,)).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM chores WHERE done=0 AND title LIKE ? ORDER BY id LIMIT 1",
            (f"%{title}%",),
        ).fetchone()
    if not row:
        raise ValueError("No matching open chore.")
    if row["done"]:
        raise ValueError("That chore is already done.")
    conn.execute("UPDATE chores SET done=1, done_at=? WHERE id=?",
                 (datetime.now().isoformat(timespec="seconds"), row["id"]))
    conn.commit()
    who = conn.execute("SELECT name FROM members WHERE id=?", (row["assignee_id"],)).fetchone()
    return {"id": row["id"], "title": row["title"], "completed_by": who["name"] if who else None}


def chore_status(conn) -> dict:
    rows = conn.execute(
        """SELECT c.id, c.title, c.effort, c.due, c.done, m.name AS assignee
           FROM chores c LEFT JOIN members m ON m.id = c.assignee_id
           ORDER BY c.done, COALESCE(c.due,'9999'), c.id"""
    ).fetchall()
    today = date.today().isoformat()
    open_chores = [dict(r) | {"overdue": bool(r["due"] and r["due"] < today)} for r in rows if not r["done"]]
    fairness = []
    for m in conn.execute("SELECT * FROM members"):
        fairness.append({"name": m["name"], "open_points": _load(conn, m["id"]),
                         "done_last_14d_points": _recent_done_load(conn, m["id"])})
    return {"open": open_chores, "workload": fairness}


# ---------------------------------------------------------------------- events
def conflicts_for(conn, member_id: int, start: datetime, end: datetime,
                  exclude_id: int | None = None) -> list[dict]:
    out = []
    for r in conn.execute("SELECT * FROM events WHERE member_id=?", (member_id,)):
        if exclude_id and r["id"] == exclude_id:
            continue
        if _overlaps(start, end, _dt(r["start"]), _dt(r["end"])):
            out.append({"id": r["id"], "title": r["title"], "start": r["start"], "end": r["end"]})
    return out


def add_event(conn, title: str, member: str, start: str, end: str, kind: str = "event") -> dict:
    s, e = _dt(start), _dt(end)
    if e <= s:
        raise ValueError("The event must end after it starts.")
    m = _member(conn, member)
    clashes = conflicts_for(conn, m["id"], s, e)
    cur = conn.execute(
        "INSERT INTO events(title, member_id, start, end, kind) VALUES (?,?,?,?,?)",
        (title.strip(), m["id"], s.isoformat(timespec="minutes"), e.isoformat(timespec="minutes"), kind),
    )
    conn.commit()
    return {"id": cur.lastrowid, "title": title.strip(), "member": m["name"],
            "start": s.isoformat(timespec="minutes"), "end": e.isoformat(timespec="minutes"),
            "conflicts": clashes}


def events_on(conn, day: str) -> list[dict]:
    d = date.fromisoformat(day)
    lo, hi = datetime.combine(d, datetime.min.time()), datetime.combine(d, datetime.max.time())
    rows = conn.execute(
        "SELECT e.*, m.name AS member FROM events e JOIN members m ON m.id=e.member_id ORDER BY e.start"
    ).fetchall()
    return [dict(r) for r in rows if _overlaps(lo, hi, _dt(r["start"]), _dt(r["end"]))]


def find_conflicts(conn, day: str) -> list[dict]:
    """Conflicts that matter to a family: same person double-booked, or
    two people who both need a ride at overlapping times with only one driver free."""
    evs = events_on(conn, day)
    found = []
    for i, a in enumerate(evs):
        for b in evs[i + 1:]:
            if a["member_id"] == b["member_id"] and _overlaps(
                _dt(a["start"]), _dt(a["end"]), _dt(b["start"]), _dt(b["end"])
            ):
                found.append({"type": "double_booked", "member": a["member"],
                              "between": [a["title"], b["title"]]})
    return found


def who_can_pickup(conn, start: str, end: str) -> list[dict]:
    s, e = _dt(start), _dt(end)
    free = []
    for m in conn.execute("SELECT * FROM members WHERE can_drive=1 ORDER BY id"):
        if not conflicts_for(conn, m["id"], s, e):
            n = conn.execute(
                "SELECT COUNT(*) FROM events WHERE member_id=? AND kind='pickup'", (m["id"],)
            ).fetchone()[0]
            free.append({"name": m["name"], "pickups_so_far": n})
    return sorted(free, key=lambda x: x["pickups_so_far"])


def assign_pickup(conn, title: str, start: str, end: str) -> dict:
    options = who_can_pickup(conn, start, end)
    if not options:
        raise ValueError("Nobody who can drive is free in that window. Consider moving it or asking a neighbour.")
    pick = options[0]["name"]
    ev = add_event(conn, title, pick, start, end, kind="pickup")
    ev["why"] = (f"{pick} is free and has done the fewest pickups"
                 f" ({options[0]['pickups_so_far']} so far); {len(options)-1} other driver(s) also free.")
    return ev


# --------------------------------------------------------------------- grocery
def grocery_add(conn, item: str, qty: str = "1", added_by: str | None = None) -> dict:
    item = item.strip()
    existing = conn.execute("SELECT * FROM grocery WHERE item=? AND bought=0", (item,)).fetchone()
    if existing:
        return {"item": item, "qty": existing["qty"], "note": "already on the list"}
    conn.execute("INSERT INTO grocery(item, qty, added_by) VALUES (?,?,?)", (item, qty, added_by))
    conn.commit()
    return {"item": item, "qty": qty, "note": "added"}


def grocery_list(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT item, qty, added_by FROM grocery WHERE bought=0 ORDER BY id")]


def grocery_bought(conn, item: str) -> dict:
    cur = conn.execute("UPDATE grocery SET bought=1 WHERE item=? AND bought=0", (item.strip(),))
    conn.commit()
    if cur.rowcount == 0:
        raise ValueError(f"'{item}' isn't on the list.")
    return {"item": item.strip(), "note": "checked off"}


# -------------------------------------------------------------------- briefing
def _fmt_time(iso: str) -> str:
    t = _dt(iso)  # portable: %-I is not supported on Windows
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def daily_briefing(conn, day: str | None = None) -> dict:
    """A voice-friendly morning briefing. `spoken` is written to be read aloud."""
    day = day or date.today().isoformat()
    evs = events_on(conn, day)
    conflicts = find_conflicts(conn, day)
    chores = chore_status(conn)
    due = [c for c in chores["open"] if c["due"] and c["due"] <= day]
    groceries = grocery_list(conn)
    pickups = [e for e in evs if e["kind"] == "pickup"]

    parts = []
    if evs:
        bits = [f"{e['member']} has {e['title']} at {_fmt_time(e['start'])}" for e in evs[:5]]
        more = f", and {len(evs) - 5} more" if len(evs) > 5 else ""
        parts.append(f"You have {len(evs)} thing{'s' if len(evs) != 1 else ''} on today. " + "; ".join(bits) + more + ".")
    else:
        parts.append("Nothing is scheduled today.")
    for c in conflicts:
        parts.append(f"Heads up: {c['member']} is double-booked between {c['between'][0]} and {c['between'][1]}.")
    if pickups:
        parts.append("Pickups: " + "; ".join(f"{p['member']} gets {p['title']} at {_fmt_time(p['start'])}" for p in pickups) + ".")
    if due:
        parts.append("Chores due: " + "; ".join(f"{c['title']} for {c['assignee']}" + (" (overdue)" if c["overdue"] else "") for c in due) + ".")
    if groceries:
        parts.append(f"The grocery list has {len(groceries)} item{'s' if len(groceries) != 1 else ''}.")
    return {"date": day, "spoken": " ".join(parts), "events": evs, "conflicts": conflicts,
            "chores_due": due, "grocery_count": len(groceries)}


# ------------------------------------------------------------------------ demo
def reset_all(conn) -> dict:
    """Wipe all household data (used for clean demo retakes)."""
    for table in ("events", "chores", "grocery", "members"):
        conn.execute(f"DELETE FROM {table}")
    conn.execute("DELETE FROM sqlite_sequence")
    conn.commit()
    return {"reset": True}


def seed_demo(conn) -> dict:
    if conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]:
        return {"seeded": False, "note": "Family already has members; not overwriting."}
    today = date.today()
    d = today.isoformat()
    add_member(conn, "Maya", "adult")
    add_member(conn, "Arjun", "adult")
    add_member(conn, "Riya", "teen")
    add_member(conn, "Kabir", "kid")
    add_event(conn, "Team standup", "Maya", f"{d}T09:30", f"{d}T10:00")
    add_event(conn, "Client call", "Maya", f"{d}T15:00", f"{d}T16:30")
    add_event(conn, "Dentist", "Arjun", f"{d}T15:30", f"{d}T16:30")
    add_event(conn, "Football practice", "Kabir", f"{d}T16:00", f"{d}T17:30")
    add_event(conn, "Robotics club", "Riya", f"{d}T16:30", f"{d}T18:00")
    add_chore(conn, "Take out recycling", 1, due=d)
    add_chore(conn, "Deep-clean kitchen", 4, due=(today + timedelta(days=2)).isoformat())
    add_chore(conn, "Laundry", 3, due=d)
    grocery_add(conn, "Milk", "2 litres", "Maya")
    grocery_add(conn, "Bananas", "6", "Kabir")
    return {"seeded": True, "family": [m["name"] for m in list_members(conn)]}
