"""
tests/test_scheduler.py
=======================
Unit tests for the kville scheduler, grace period logic, and fairness reporting.

Run with:
  pytest tests/
"""

import pytest
from datetime import datetime, timedelta
from kville.models import (
    Member, Settings, GracePeriod, Game, Trade, Phase,
    PHASES, NIGHT_HOURS, AVAIL_GREEN, AVAIL_YELLOW, AVAIL_RED,
    is_night_slot, slot_key, parse_slot_key,
)
from kville.scheduler import (
    get_week_start, total_hours, all_hours, required_count,
    generate_schedule, fairness_report, coverage_gaps,
)
from kville.grace import (
    is_grace, grace_for_game, grace_after_check, grace_weather,
    rebuild_game_graces,
)


# ── Fixtures ──────────────────────────────────────────────────

def make_members(n: int = 4) -> list[Member]:
    colors = ["#e74c3c","#27ae60","#2980b9","#8e44ad","#e67e22",
              "#16a085","#c0392b","#1abc9c","#e91e63","#ff5722",
              "#3498db","#d4ac0d"]
    return [Member(id=f"m{i+1}", name=f"Member {i+1}", color=colors[i]) for i in range(n)]


def make_settings(phase: str = "blue") -> Settings:
    return Settings(current_phase=phase)


WEEK = datetime(2026, 1, 19)  # a Monday


# ── slot_key / parse_slot_key ─────────────────────────────────

class TestSlotKey:
    def test_roundtrip(self):
        d = datetime(2026, 1, 25)
        for h in [0, 4, 12, 22]:
            key = slot_key(d, h)
            dt2, h2 = parse_slot_key(key)
            assert dt2.date() == d.date()
            assert h2 == h

    def test_format(self):
        d = datetime(2026, 1, 19)
        assert slot_key(d, 8) == "2026-01-19-08"

    def test_night_hours(self):
        assert is_night_slot(2)
        assert is_night_slot(4)
        assert not is_night_slot(0)
        assert not is_night_slot(6)
        assert not is_night_slot(22)


# ── get_week_start ────────────────────────────────────────────

class TestGetWeekStart:
    def test_sunday_unchanged(self):
        sun = datetime(2026, 1, 18)  # Sunday
        assert get_week_start(sun).weekday() == 6  # weekday 6 = Sunday

    def test_monday_goes_back_to_sunday(self):
        mon = datetime(2026, 1, 19)
        ws = get_week_start(mon)
        assert ws == datetime(2026, 1, 18)

    def test_saturday_goes_back_to_sunday(self):
        sat = datetime(2026, 1, 24)
        ws = get_week_start(sat)
        assert ws == datetime(2026, 1, 18)


# ── required_count ────────────────────────────────────────────

class TestRequiredCount:
    def test_blue_day(self):
        assert required_count(8, "blue") == PHASES["blue"].day_required

    def test_blue_night(self):
        assert required_count(2, "blue") == PHASES["blue"].night_required
        assert required_count(4, "blue") == PHASES["blue"].night_required

    def test_black_night_higher_than_day(self):
        assert required_count(2, "black") > required_count(8, "black")


# ── generate_schedule ─────────────────────────────────────────

class TestGenerateSchedule:
    def test_green_members_preferred(self):
        members  = make_members(4)
        settings = make_settings("white")  # day_required=1

        week_start = get_week_start(WEEK)
        day        = week_start
        hour       = 8
        key        = slot_key(day, hour)

        # m1 = green, m2 = yellow, m3–m4 = unset (red)
        avail = {
            "m1": {key: AVAIL_GREEN},
            "m2": {key: AVAIL_YELLOW},
        }

        schedule = generate_schedule(week_start, members, avail, settings)
        assigned = schedule.get(key, [])
        assert "m1" in assigned
        assert "m2" not in assigned   # only 1 required for white day

    def test_yellow_used_when_no_green(self):
        members  = make_members(4)
        settings = make_settings("white")

        week_start = get_week_start(WEEK)
        key        = slot_key(week_start, 8)

        avail = {"m2": {key: AVAIL_YELLOW}}
        schedule = generate_schedule(week_start, members, avail, settings)
        assert "m2" in schedule.get(key, [])

    def test_red_never_assigned(self):
        members  = make_members(4)
        settings = make_settings("white")

        week_start = get_week_start(WEEK)
        key        = slot_key(week_start, 8)

        avail = {"m1": {key: AVAIL_RED}}
        schedule = generate_schedule(week_start, members, avail, settings)
        assert "m1" not in schedule.get(key, [])

    def test_existing_slots_not_overwritten(self):
        members    = make_members(4)
        settings   = make_settings("white")
        week_start = get_week_start(WEEK)
        key        = slot_key(week_start, 8)

        existing = {key: ["m4"]}
        avail    = {"m1": {key: AVAIL_GREEN}}
        schedule = generate_schedule(week_start, members, avail, settings, existing=existing)
        assert schedule[key] == ["m4"]   # untouched

    def test_grace_slots_get_empty_list(self):
        members    = make_members(4)
        week_start = get_week_start(WEEK)
        key        = slot_key(week_start, 10)
        dt, h      = parse_slot_key(key)

        gp = GracePeriod(
            id    = "gp_test",
            start = dt.replace(hour=9).isoformat(),
            end   = dt.replace(hour=13).isoformat(),
            reason= "test grace",
        )
        settings = Settings(current_phase="white", grace_periods=[gp])
        avail    = {"m1": {key: AVAIL_GREEN}}
        schedule = generate_schedule(week_start, members, avail, settings)
        assert schedule.get(key) == []

    def test_fairness_lower_hours_preferred(self):
        """Under equal green availability, member with fewer hours should be chosen first."""
        members  = make_members(2)
        settings = make_settings("white")

        week_start  = get_week_start(WEEK)
        key1        = slot_key(week_start, 8)
        key2        = slot_key(week_start, 10)

        # Both green for both slots
        avail = {
            "m1": {key1: AVAIL_GREEN, key2: AVAIL_GREEN},
            "m2": {key1: AVAIL_GREEN, key2: AVAIL_GREEN},
        }

        # Pre-assign key1 to m1 so m1 has 2h more than m2
        existing = {key1: ["m1"]}
        schedule = generate_schedule(week_start, members, avail, settings, existing=existing)
        # m2 should be assigned to key2 since m1 already has hours
        assert "m2" in schedule.get(key2, [])


# ── fairness_report ───────────────────────────────────────────

class TestFairnessReport:
    def test_average_correct(self):
        members = make_members(2)
        schedule = {
            "2026-01-19-08": ["m1"],
            "2026-01-19-10": ["m2"],
            "2026-01-19-12": ["m1"],
        }
        report = fairness_report(schedule, members)
        # m1 = 4h, m2 = 2h → avg = 3
        assert report["average_hours"] == 3.0

    def test_flag_for_large_diff(self):
        members  = make_members(2)
        schedule = {f"2026-01-19-{h:02d}": ["m1"] for h in range(0, 20, 2)}
        report   = fairness_report(schedule, members)
        m1_entry = next(r for r in report["members"] if r["id"] == "m1")
        m2_entry = next(r for r in report["members"] if r["id"] == "m2")
        assert m1_entry["flag"]
        assert m2_entry["flag"]

    def test_no_flag_for_equal_distribution(self):
        members  = make_members(2)
        schedule = {
            "2026-01-19-08": ["m1"],
            "2026-01-19-10": ["m2"],
        }
        report = fairness_report(schedule, members)
        for r in report["members"]:
            assert not r["flag"]


# ── coverage_gaps ─────────────────────────────────────────────

class TestCoverageGaps:
    def test_under_staffed_slot_is_gap(self):
        members    = make_members(4)
        settings   = make_settings("white")  # day_required=1
        week_start = get_week_start(WEEK)
        key        = slot_key(week_start, 8)

        # Empty schedule
        gaps = coverage_gaps({}, settings, week_start)
        assert key in gaps

    def test_fully_staffed_not_gap(self):
        settings   = make_settings("white")  # day_required=1
        week_start = get_week_start(WEEK)
        key        = slot_key(week_start, 8)

        schedule = {key: ["m1"]}
        gaps     = coverage_gaps(schedule, settings, week_start)
        assert key not in gaps

    def test_grace_slot_not_a_gap(self):
        week_start = get_week_start(WEEK)
        key        = slot_key(week_start, 8)
        dt, h      = parse_slot_key(key)

        gp = GracePeriod(
            id    = "gp_test",
            start = dt.replace(hour=7).isoformat(),
            end   = dt.replace(hour=11).isoformat(),
            reason= "test",
        )
        settings = Settings(current_phase="white", grace_periods=[gp])
        gaps     = coverage_gaps({}, settings, week_start)
        assert key not in gaps


# ── Grace period helpers ──────────────────────────────────────

class TestGraceHelpers:
    def test_is_grace_detects_overlap(self):
        now = datetime(2026, 1, 20, 10, 0)
        gp  = GracePeriod(
            id    = "gp1",
            start = "2026-01-20T09:00:00",
            end   = "2026-01-20T11:30:00",
            reason= "test",
        )
        # Slot 10:00–12:00 overlaps the grace 09:00–11:30
        assert is_grace(datetime(2026, 1, 20), 10, [gp])
        # Slot 12:00–14:00 does not overlap
        assert not is_grace(datetime(2026, 1, 20), 12, [gp])

    def test_grace_for_home_game_is_2h(self):
        game = Game(
            id       = "g1",
            opponent = "UNC",
            date     = "2026-02-06",
            time     = "21:00",
            is_home  = True,
        )
        gp = grace_for_game(game)
        start = datetime.fromisoformat(gp.start)
        end   = datetime.fromisoformat(gp.end)
        assert end - start == timedelta(hours=4)  # 2h before + 2h after

    def test_grace_for_away_game_is_1h(self):
        game = Game(
            id       = "g2",
            opponent = "Virginia",
            date     = "2026-02-12",
            time     = "20:00",
            is_home  = False,
        )
        gp = grace_for_game(game)
        start = datetime.fromisoformat(gp.start)
        end   = datetime.fromisoformat(gp.end)
        assert end - start == timedelta(hours=2)  # 1h before + 1h after

    def test_grace_weather(self):
        now = datetime(2026, 1, 15, 7, 0)
        gp  = grace_weather(now, hours=3)
        end = datetime.fromisoformat(gp.end)
        assert (end - now) == timedelta(hours=3)
        assert "weather" in gp.reason.lower()

    def test_rebuild_game_graces_replaces_old(self):
        game = Game(
            id       = "g1",
            opponent = "UNC",
            date     = "2026-02-06",
            time     = "21:00",
            is_home  = True,
        )
        # Start with a stale game grace
        old_gp = GracePeriod(id="grace_game_g1", start="2026-01-01T00:00:00",
                             end="2026-01-01T04:00:00", reason="stale")
        settings = Settings(
            current_phase = "blue",
            games         = [game],
            grace_periods = [old_gp],
        )
        new_settings = rebuild_game_graces(settings)
        game_graces  = [gp for gp in new_settings.grace_periods if gp.id == "grace_game_g1"]
        assert len(game_graces) == 1
        assert game_graces[0].start != old_gp.start   # replaced with correct time


# ── total_hours / all_hours ───────────────────────────────────

class TestHoursHelpers:
    def test_total_hours(self):
        schedule = {
            "2026-01-19-08": ["m1", "m2"],
            "2026-01-19-10": ["m1"],
        }
        assert total_hours(schedule, "m1") == 4
        assert total_hours(schedule, "m2") == 2
        assert total_hours(schedule, "m3") == 0

    def test_all_hours(self):
        members  = make_members(3)
        schedule = {
            "2026-01-19-08": ["m1", "m2"],
            "2026-01-19-10": ["m3"],
        }
        h = all_hours(schedule, members)
        assert h["m1"] == 2
        assert h["m2"] == 2
        assert h["m3"] == 2
