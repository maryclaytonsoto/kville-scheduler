"""
kville.models
=============
Dataclasses for every entity in the K-Ville scheduler.
All objects are plain Python dataclasses so they serialize
cleanly to/from JSON via dataclasses.asdict().
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ── Availability states ───────────────────────────────────────
AVAIL_NONE   = "none"
AVAIL_GREEN  = "green"    # prefer to be scheduled
AVAIL_YELLOW = "yellow"   # available but prefer not
AVAIL_RED    = "red"      # unavailable


# ── Tenting phase rules ───────────────────────────────────────
#  Headcounts from official K-Ville policy (Line Monitor Committee)
#  Day hours  : 7:00 AM – 2:30 AM  (slots at 0,6,8,10,12,14,16,18,20,22)
#  Night hours: 2:30 AM – 7:00 AM  (slots at 2, 4)

PHASES: dict[str, "Phase"] = {}   # populated after Phase is defined

@dataclass
class Phase:
    key: str
    label: str
    day_required: int    # min members during day hours
    night_required: int  # min members during night hours (2:30–7 AM)


PHASES["black"] = Phase("black", "Black Tenting",     day_required=2,  night_required=10)
PHASES["blue"]  = Phase("blue",  "Blue Tenting",      day_required=1,  night_required=6)
PHASES["white"] = Phase("white", "White / Flex",      day_required=1,  night_required=2)


# ── 2-hour slot definitions ───────────────────────────────────
SLOT_HOURS  = list(range(0, 24, 2))   # [0, 2, 4, …, 22]
NIGHT_HOURS = {2, 4}                  # slots whose start hour is in night window


def is_night_slot(hour: int) -> bool:
    return hour in NIGHT_HOURS


def slot_key(date: datetime, hour: int) -> str:
    """Canonical key: 'YYYY-MM-DD-HH'."""
    return f"{date.strftime('%Y-%m-%d')}-{hour:02d}"


def parse_slot_key(key: str) -> tuple[datetime, int]:
    """Return (date, hour) from a slot key string."""
    parts = key.split("-")
    year, month, day, hour = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    return datetime(year, month, day, hour), hour


# ── Core entities ─────────────────────────────────────────────

@dataclass
class Member:
    id: str
    name: str
    color: str = "#012169"
    photo_url: Optional[str] = None


@dataclass
class GracePeriod:
    id: str
    start: str        # ISO 8601 datetime string
    end: str          # ISO 8601 datetime string
    reason: str = ""

    def covers(self, slot_start: datetime, slot_end: datetime) -> bool:
        gp_start = datetime.fromisoformat(self.start)
        gp_end   = datetime.fromisoformat(self.end)
        return slot_start < gp_end and slot_end > gp_start


@dataclass
class Game:
    id: str
    date: str          # YYYY-MM-DD
    time: str          # HH:MM (24h)
    opponent: str = "TBD"
    is_home: bool = True

    def tipoff(self) -> datetime:
        return datetime.fromisoformat(f"{self.date}T{self.time}")


@dataclass
class Settings:
    current_phase: str = "blue"
    game_date: str = ""                        # YYYY-MM-DD of UNC game
    grace_periods: list[GracePeriod] = field(default_factory=list)
    games: list[Game] = field(default_factory=list)
    pchecks: dict[str, int] = field(default_factory=dict)   # member_id → count (0-5)


@dataclass
class Trade:
    id: str
    poster_id: str
    slot_key: str
    note: str = ""
    status: str = "open"         # "open" | "accepted"
    acceptor_id: Optional[str] = None
    created_ts: float = 0.0
    accepted_ts: Optional[float] = None
