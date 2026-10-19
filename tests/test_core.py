import pytest

from homebase import core

D = "2026-10-20"


@pytest.fixture
def conn(tmp_path):
    c = core.connect(str(tmp_path / "t.db"))
    core.add_member(c, "Maya", "adult")
    core.add_member(c, "Arjun", "adult")
    core.add_member(c, "Kabir", "kid")
    yield c
    c.close()


def test_duplicate_member_rejected(conn):
    with pytest.raises(ValueError):
        core.add_member(conn, "maya")


def test_kid_cannot_drive_by_default(conn):
    assert not [m for m in core.list_members(conn) if m["name"] == "Kabir"][0]["can_drive"]


def test_chore_fairness_spreads_work(conn):
    first = core.add_chore(conn, "A", 4)["assignee"]
    second = core.add_chore(conn, "B", 4)["assignee"]
    assert first != second  # heavy chores don't pile on one person


def test_hard_chores_skip_kids(conn):
    for _ in range(4):
        assert core.add_chore(conn, "Heavy", 5)["assignee"] != "Kabir"


def test_complete_chore_by_title(conn):
    core.add_chore(conn, "Take out recycling", 1)
    assert core.complete_chore(conn, title="recycling")["title"] == "Take out recycling"
    with pytest.raises(ValueError):
        core.complete_chore(conn, title="recycling")


def test_event_conflict_detected(conn):
    core.add_event(conn, "Dentist", "Arjun", f"{D}T15:30", f"{D}T16:30")
    r = core.add_event(conn, "Meeting", "Arjun", f"{D}T16:00", f"{D}T17:00")
    assert len(r["conflicts"]) == 1
    assert core.find_conflicts(conn, D)[0]["member"] == "Arjun"


def test_back_to_back_is_not_a_conflict(conn):
    core.add_event(conn, "A", "Maya", f"{D}T10:00", f"{D}T11:00")
    assert core.add_event(conn, "B", "Maya", f"{D}T11:00", f"{D}T12:00")["conflicts"] == []


def test_bad_times_rejected(conn):
    with pytest.raises(ValueError):
        core.add_event(conn, "X", "Maya", f"{D}T12:00", f"{D}T11:00")
    with pytest.raises(ValueError):
        core.add_event(conn, "X", "Maya", "tomorrow-ish", f"{D}T11:00")


def test_unknown_member_gives_helpful_error(conn):
    with pytest.raises(ValueError, match="Known members"):
        core.add_event(conn, "X", "Nobody", f"{D}T10:00", f"{D}T11:00")


def test_pickup_goes_to_free_driver_and_rotates(conn):
    core.add_event(conn, "Client call", "Maya", f"{D}T17:00", f"{D}T18:00")
    r = core.assign_pickup(conn, "Pickup 1", f"{D}T17:30", f"{D}T18:00")
    assert r["member"] == "Arjun"  # Maya is busy, kids can't drive
    r2 = core.assign_pickup(conn, "Pickup 2", f"{D}T19:00", f"{D}T19:30")
    assert r2["member"] == "Maya"  # rotation: Arjun already has one


def test_pickup_none_free(conn):
    for n in ("Maya", "Arjun"):
        core.add_event(conn, "Busy", n, f"{D}T17:00", f"{D}T18:00")
    with pytest.raises(ValueError, match="free"):
        core.assign_pickup(conn, "P", f"{D}T17:15", f"{D}T17:45")


def test_grocery_dedupe_and_check_off(conn):
    core.grocery_add(conn, "Milk")
    assert core.grocery_add(conn, "milk")["note"] == "already on the list"
    assert len(core.grocery_list(conn)) == 1
    core.grocery_bought(conn, "Milk")
    assert core.grocery_list(conn) == []


def test_briefing_mentions_conflict(conn):
    core.add_event(conn, "Dentist", "Arjun", f"{D}T15:30", f"{D}T16:30")
    core.add_event(conn, "Meeting", "Arjun", f"{D}T16:00", f"{D}T17:00")
    assert "double-booked" in core.daily_briefing(conn, D)["spoken"]


def test_seed_demo_is_idempotent(tmp_path):
    c = core.connect(str(tmp_path / "s.db"))
    assert core.seed_demo(c)["seeded"] is True
    assert core.seed_demo(c)["seeded"] is False
