"""
kville.grace
============
Grace-period logic.

Official rules (K-Ville policy):
  - 1 hour after each tent check completes
  - 2 hours before AND after a home men's/women's basketball game
  - 1 hour before AND after an away men's/women's basketball game
  - Weather: temp < 25 F, snow > 2 in, wind > 35 mph, lightning within
    6 miles, severe weather warnings, icy conditions, school closure
  - Any time at Head Line Monitor discretion
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kville.models import Game, GracePeriod, Settings

from kville.models import GracePeriod, slot_key, SLOT_HOURS


def is_grace(slot_dt: datetime, hour: int, grace_periods: list["GracePeriod"]) -> bool:
    """Return True if the 2-hour slot starting at slot_dt/hour overlaps any grace period."""
    if not grace_periods:
        return False
    slot_start = slot_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    slot_end   = slot_start + timedelta(hours=2)
    return any(gp.covers(slot_start, slot_end) for gp in grace_periods)


def grace_for_game(game: "Game") -> GracePeriod:
    """
    Auto-generate a grace period for a scheduled game.
      Home game : 2 h before tipoff → 2 h after tipoff
      Away game : 1 h before tipoff → 1 h after tipoff
    """
    tipoff  = game.tipoff()
    buffer  = timedelta(hours=2 if game.is_home else 1)
    label   = ("Home" if game.is_home else "Away") + f" game vs {game.opponent}"
    return GracePeriod(
        id     = f"grace_game_{game.id}",
        start  = (tipoff - buffer).isoformat(),
        end    = (tipoff + buffer).isoformat(),
        reason = f"Auto-grace: {label} ({buffer.seconds // 3600}h before & after)",
    )


def grace_after_check(check_time: datetime, hours: int = 1) -> GracePeriod:
    """Grace period granted for `hours` after a tent check completes."""
    gid = f"grace_check_{int(check_time.timestamp())}"
    return GracePeriod(
        id     = gid,
        start  = check_time.isoformat(),
        end    = (check_time + timedelta(hours=hours)).isoformat(),
        reason = f"Post-check grace ({hours}h)",
    )


def grace_weather(start: datetime, hours: int = 3) -> GracePeriod:
    """Manually triggered weather grace period."""
    gid = f"grace_weather_{int(start.timestamp())}"
    return GracePeriod(
        id     = gid,
        start  = start.isoformat(),
        end    = (start + timedelta(hours=hours)).isoformat(),
        reason = f"Weather grace — {hours}h",
    )


def rebuild_game_graces(settings: "Settings") -> "Settings":
    """
    Recompute all game-derived grace periods from settings.games,
    replacing any existing 'grace_game_*' entries.
    Returns a new Settings object with updated grace_periods.
    """
    import copy
    s = copy.deepcopy(settings)
    # Remove old game-graces
    s.grace_periods = [gp for gp in s.grace_periods if not gp.id.startswith("grace_game_")]
    # Re-add from current games list
    for game in s.games:
        s.grace_periods.append(grace_for_game(game))
    return s
