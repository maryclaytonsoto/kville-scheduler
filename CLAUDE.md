# CLAUDE.md — K-Ville Tent Scheduler

Context for AI assistants working in this repository.

## What this project is

A scheduling tool for Duke Basketball K-Ville tenting groups. Twelve members take turns staying in a tent outside Cameron Indoor Stadium to secure tickets to the UNC game. The app tracks availability, generates fair tent-shift schedules, handles grace periods (games, weather, post-checks), manages shift trades, and records P-Check attendance.

There are two deliverables that work together:

1. **`kville-scheduler.html`** — a single-file browser app (React 18 + Babel Standalone + Tailwind CDN) that serves as the primary user-facing interface. No build step required; just open in a browser. Firebase optional for multi-device sync.

2. **Python package (`kville/`)** — a CLI and importable package for schedule generation, data management, and scripting. Entry point: `kville_schedule.py`.

## Repository layout

```
TeamSchedule/
├── kville-scheduler.html    # Full browser app (single file)
├── kville_schedule.py       # CLI entry point
├── kville/
│   ├── __init__.py          # Re-exports all public symbols
│   ├── models.py            # Dataclasses + constants
│   ├── scheduler.py         # Schedule generation algorithm
│   ├── grace.py             # Grace period helpers
│   └── storage.py           # JSON load/save
├── data/
│   ├── members.json         # Member roster (edit names here)
│   ├── settings.json        # Phase, games, grace periods, pchecks
│   ├── availability.json    # {member_id: {slot_key: avail_state}}
│   ├── schedule.json        # {slot_key: [member_id, ...]}
│   └── trades.json          # List of Trade objects
├── tests/
│   ├── __init__.py
│   └── test_scheduler.py    # pytest unit tests
├── requirements.txt
├── .gitignore
└── CLAUDE.md
```

## Key constants (must stay in sync between HTML and Python)

| Constant | Value | Source |
|---|---|---|
| `SLOT_HOURS` | `[0,2,4,6,8,10,12,14,16,18,20,22]` | `kville/models.py` |
| `NIGHT_HOURS` | `{2, 4}` (covering 2:30 AM–7 AM) | `kville/models.py` |
| `PHASES["black"]` | day=2, night=10 | `kville/models.py` |
| `PHASES["blue"]` | day=1, night=6 | `kville/models.py` |
| `PHASES["white"]` | day=1, night=2 | `kville/models.py` |
| Availability states | `"green"`, `"yellow"`, `"red"`, `""` | `kville/models.py` |

Slot keys use format `YYYY-MM-DD-HH` (zero-padded hour).

## Tenting rules encoded

Based on official K-Ville / Line Monitor policy:
- **P-Checks**: 5 random checks over 2 nights; need 3/5 to earn a wristband
- **Grace periods auto-generated** when a game is added: 2h buffer each side for home games, 1h for away
- **Post-check grace**: 1h after a check completes (no penalty for leaving immediately after)
- **Weather grace**: manual trigger; typical duration 3h

## Scheduling algorithm (scheduler.py)

1. Iterate 7 days × 12 slots per day
2. Skip slots already assigned in `existing` or falling in a grace period
3. Determine `required_count` from phase (day vs. night slot)
4. Sort eligible members: green availability first, then yellow; ties broken by fewest cumulative scheduled hours
5. Assign first `required_count` sorted candidates
6. Increment running hour totals

Never assign members with red or unset availability.

## Data files

`members.json` — edit names and colors before first use. IDs (`m1`–`m12`) are referenced throughout availability and schedule files; don't change IDs after data exists.

`settings.json` — the UNC game is seeded as `"unc_2026"`. Update `tipoff_iso` each season. `pchecks` is a dict `{member_id: count}`.

`availability.json` and `schedule.json` are generated at runtime; don't manually edit unless debugging.

## Running the CLI

```bash
# Requires Python 3.10+
pip install -r requirements.txt --break-system-packages

python kville_schedule.py --help
python kville_schedule.py generate
python kville_schedule.py show
python kville_schedule.py fairness
python kville_schedule.py phase --set blue
python kville_schedule.py grace --weather 3
python kville_schedule.py pchecks
```

## Running tests

```bash
pytest tests/ -v
```

## Firebase sync (HTML app)

Near the top of `kville-scheduler.html`, find:

```js
const FIREBASE_CONFIG = null;
```

Replace `null` with your Firebase project config object to enable real-time sync across all 12 members' devices. Leave as `null` to use localStorage only (single-device mode).

## Common tasks for AI assistants

**Add a new member**: update `data/members.json` (add entry with unique id like `m13`) and regenerate availability.

**Change the tenting phase**: `python kville_schedule.py phase --set black` or edit `settings.json`.

**Add a game**: add to `games` array in `settings.json` with `id`, `opponent`, `tipoff_iso` (ISO 8601), `is_home` (bool). Grace periods auto-regenerate on next `load_settings()` call via `rebuild_game_graces`.

**Regenerate schedule after availability changes**: `python kville_schedule.py generate --week YYYY-MM-DD`.

**Check fairness**: `python kville_schedule.py fairness` — members flagged with ⚠ are >4h above/below average.
