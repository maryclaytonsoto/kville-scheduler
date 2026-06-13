"""
kville.storage
==============
JSON-based persistence layer.

Data is stored in a single directory (default: ./data/) as separate
JSON files so each piece can be version-controlled independently.

Files
-----
  members.json      – list of Member objects
  settings.json     – Settings object (phase, game date, grace periods, games, pchecks)
  availability.json – nested dict  {member_id: {slot_key: avail_state}}
  schedule.json     – dict         {slot_key: [member_id, ...]}
  trades.json       – list of Trade objects
"""

from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from kville.models import Member, Settings, GracePeriod, Game, Trade


DATA_DIR = Path(__file__).parent.parent / "data"


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def _save(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(obj, f, indent=2)


# ── Members ───────────────────────────────────────────────────

def load_members(data_dir: Path = DATA_DIR) -> list[Member]:
    raw = _load(data_dir / "members.json")
    if raw is None:
        return _default_members()
    return [Member(**m) for m in raw]


def save_members(members: list[Member], data_dir: Path = DATA_DIR) -> None:
    _save(data_dir / "members.json", [asdict(m) for m in members])


def _default_members() -> list[Member]:
    colors = [
        "#e74c3c","#e67e22","#d4ac0d","#27ae60","#16a085",
        "#2980b9","#8e44ad","#c0392b","#1abc9c","#e91e63",
        "#ff5722","#3498db",
    ]
    return [Member(id=f"m{i+1}", name=f"Member {i+1}", color=colors[i]) for i in range(12)]


# ── Settings ──────────────────────────────────────────────────

def load_settings(data_dir: Path = DATA_DIR) -> Settings:
    raw = _load(data_dir / "settings.json")
    if raw is None:
        return Settings()
    gps   = [GracePeriod(**g) for g in raw.get("grace_periods", [])]
    games = [Game(**g)        for g in raw.get("games", [])]
    return Settings(
        current_phase  = raw.get("current_phase", "blue"),
        game_date      = raw.get("game_date", ""),
        grace_periods  = gps,
        games          = games,
        pchecks        = raw.get("pchecks", {}),
    )


def save_settings(settings: Settings, data_dir: Path = DATA_DIR) -> None:
    d = asdict(settings)
    _save(data_dir / "settings.json", d)


# ── Availability ──────────────────────────────────────────────

def load_availability(data_dir: Path = DATA_DIR) -> dict[str, dict[str, str]]:
    return _load(data_dir / "availability.json") or {}


def save_availability(avail: dict[str, dict[str, str]], data_dir: Path = DATA_DIR) -> None:
    _save(data_dir / "availability.json", avail)


# ── Schedule ──────────────────────────────────────────────────

def load_schedule(data_dir: Path = DATA_DIR) -> dict[str, list[str]]:
    return _load(data_dir / "schedule.json") or {}


def save_schedule(schedule: dict[str, list[str]], data_dir: Path = DATA_DIR) -> None:
    _save(data_dir / "schedule.json", schedule)


# ── Trades ────────────────────────────────────────────────────

def load_trades(data_dir: Path = DATA_DIR) -> list[Trade]:
    raw = _load(data_dir / "trades.json")
    if raw is None:
        return []
    return [Trade(**t) for t in raw]


def save_trades(trades: list[Trade], data_dir: Path = DATA_DIR) -> None:
    _save(data_dir / "trades.json", [asdict(t) for t in trades])


# ── Convenience: load/save everything at once ─────────────────

def load_all(data_dir: Path = DATA_DIR) -> dict:
    return {
        "members":      load_members(data_dir),
        "settings":     load_settings(data_dir),
        "availability": load_availability(data_dir),
        "schedule":     load_schedule(data_dir),
        "trades":       load_trades(data_dir),
    }


def save_all(
    members: list[Member],
    settings: Settings,
    availability: dict,
    schedule: dict,
    trades: list[Trade],
    data_dir: Path = DATA_DIR,
) -> None:
    save_members(members, data_dir)
    save_settings(settings, data_dir)
    save_availability(availability, data_dir)
    save_schedule(schedule, data_dir)
    save_trades(trades, data_dir)
