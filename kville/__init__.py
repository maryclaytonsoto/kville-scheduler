"""
kville — K-Ville Tent Scheduler Python package.

Submodules
----------
  models    – dataclasses: Member, Settings, GracePeriod, Game, Trade, Phase
  scheduler – schedule generation algorithm and fairness reporting
  grace     – grace period helpers (game auto-grace, weather grace, post-check grace)
  storage   – JSON-based load/save for all data files
"""

from kville.models import (
    Member, Settings, GracePeriod, Game, Trade, Phase,
    PHASES, SLOT_HOURS, NIGHT_HOURS,
    is_night_slot, slot_key, parse_slot_key,
    AVAIL_NONE, AVAIL_GREEN, AVAIL_YELLOW, AVAIL_RED,
)
from kville.scheduler import (
    generate_schedule, fairness_report, coverage_gaps,
    get_week_start, total_hours, all_hours,
)
from kville.grace import (
    is_grace, grace_for_game, grace_after_check,
    grace_weather, rebuild_game_graces,
)
from kville.storage import (
    load_all, save_all,
    load_members, save_members,
    load_settings, save_settings,
    load_availability, save_availability,
    load_schedule, save_schedule,
    load_trades, save_trades,
)

__version__ = "0.1.0"
__all__ = [
    "Member", "Settings", "GracePeriod", "Game", "Trade", "Phase",
    "PHASES", "SLOT_HOURS", "NIGHT_HOURS",
    "is_night_slot", "slot_key", "parse_slot_key",
    "AVAIL_NONE", "AVAIL_GREEN", "AVAIL_YELLOW", "AVAIL_RED",
    "generate_schedule", "fairness_report", "coverage_gaps",
    "get_week_start", "total_hours", "all_hours",
    "is_grace", "grace_for_game", "grace_after_check",
    "grace_weather", "rebuild_game_graces",
    "load_all", "save_all",
    "load_members", "save_members",
    "load_settings", "save_settings",
    "load_availability", "save_availability",
    "load_schedule", "save_schedule",
    "load_trades", "save_trades",
]
