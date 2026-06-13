"""
kville.scheduler
================
Core schedule generation algorithm.

Priority order for assigning members to a slot:
  1. Members with green availability (prefer to be scheduled)
  2. Members with yellow availability (available but prefer not)
  3. Never assign red or unset members

Within each preference tier, members with fewer total scheduled hours
are preferred to distribute the burden evenly.

Night slots (hours 2 and 4, covering the 2:30 AM – 7 AM window) use
the phase's night_required headcount; all other slots use day_required.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from kville.models import (
    Member, Settings, PHASES, SLOT_HOURS,
    is_night_slot, slot_key, AVAIL_GREEN, AVAIL_YELLOW, AVAIL_RED,
)
from kville.grace import is_grace


# Type aliases
Schedule     = dict[str, list[str]]     # slot_key → [member_id, ...]
Availability = dict[str, dict[str, str]]  # member_id → {slot_key → avail_state}


def get_week_start(date: datetime) -> datetime:
    """Return the Sunday 00:00:00 of the week containing `date`."""
    d = date.replace(hour=0, minute=0, second=0, microsecond=0)
    return d - timedelta(days=d.weekday() + 1) if d.weekday() != 6 else d


def total_hours(schedule: Schedule, member_id: str) -> int:
    """Return the total scheduled hours for a member (each slot = 2 h)."""
    return sum(2 for assigned in schedule.values() if member_id in assigned)


def all_hours(schedule: Schedule, members: list[Member]) -> dict[str, int]:
    """Return {member_id: hours} for all members."""
    counts: dict[str, int] = {m.id: 0 for m in members}
    for assigned in schedule.values():
        for mid in assigned:
            if mid in counts:
                counts[mid] += 2
    return counts


def required_count(hour: int, phase_key: str) -> int:
    """Return the minimum number of members needed in the tent for this slot."""
    phase = PHASES[phase_key]
    return phase.night_required if is_night_slot(hour) else phase.day_required


def generate_schedule(
    week_start: datetime,
    members: list[Member],
    availability: Availability,
    settings: Settings,
    existing: Optional[Schedule] = None,
) -> Schedule:
    """
    Generate (or extend) a schedule for the 7 days starting at `week_start`.

    Slots that are already assigned in `existing` are left untouched.
    Grace-period slots get an empty assignment list (no coverage needed).

    Returns a new Schedule dict.
    """
    schedule: Schedule = dict(existing or {})

    # Running hour totals so we can favour under-scheduled members
    running: dict[str, int] = {m.id: total_hours(schedule, m.id) for m in members}

    for day_offset in range(7):
        day = week_start + timedelta(days=day_offset)

        for hour in SLOT_HOURS:
            key = slot_key(day, hour)

            # Skip already-assigned slots
            if key in schedule and schedule[key]:
                continue

            # Grace period — no assignment needed
            if is_grace(day, hour, settings.grace_periods):
                schedule[key] = []
                continue

            req = required_count(hour, settings.current_phase)

            # Rank members: green first, then yellow; ties broken by fewer hours
            def rank(m: Member) -> tuple[int, int]:
                avail = (availability.get(m.id) or {}).get(key, AVAIL_RED)
                tier  = 0 if avail == AVAIL_GREEN else 1 if avail == AVAIL_YELLOW else 999
                return (tier, running[m.id])

            candidates = [
                m for m in members
                if (availability.get(m.id) or {}).get(key) in (AVAIL_GREEN, AVAIL_YELLOW)
            ]
            candidates.sort(key=rank)

            assigned = [m.id for m in candidates[:req]]
            schedule[key] = assigned
            for mid in assigned:
                running[mid] = running.get(mid, 0) + 2

    return schedule


def fairness_report(schedule: Schedule, members: list[Member]) -> dict:
    """
    Return a summary dict with per-member hours, the group average,
    and a flag for any member who is more than 4 hours over/under.
    """
    hours = all_hours(schedule, members)
    total = sum(hours.values())
    avg   = total / len(members) if members else 0
    report = {
        "average_hours": round(avg, 1),
        "members": [],
    }
    for m in members:
        h    = hours[m.id]
        diff = h - avg
        report["members"].append({
            "id":     m.id,
            "name":   m.name,
            "hours":  h,
            "diff":   round(diff, 1),
            "flag":   abs(diff) > 4,
        })
    report["members"].sort(key=lambda r: r["hours"])
    return report


def coverage_gaps(
    schedule: Schedule,
    settings: Settings,
    week_start: datetime,
) -> list[str]:
    """
    Return a list of slot keys where assigned headcount is below the
    required minimum and the slot is not a grace period.
    """
    gaps = []
    for day_offset in range(7):
        day = week_start + timedelta(days=day_offset)
        for hour in SLOT_HOURS:
            key = slot_key(day, hour)
            if is_grace(day, hour, settings.grace_periods):
                continue
            req      = required_count(hour, settings.current_phase)
            assigned = schedule.get(key, [])
            if len(assigned) < req:
                gaps.append(key)
    return gaps
