# K-Ville Tent Scheduler

Schedule management tool for Duke Basketball K-Ville tenting groups.

## What it does

- **Availability input** — each of 12 members marks time slots green / yellow / red
- **Auto-schedule** — generates a fair weekly schedule respecting phase headcount rules
- **Grace periods** — auto-blocks game windows, weather graces, and post-check windows
- **Trade board** — members post and accept shift swaps; schedule updates automatically
- **P-Check tracking** — records attendance across the 5-check wristband cycle
- **Fairness reporting** — flags any member who is >4h over or under the group average

## Two ways to use it

### 1. Browser app (recommended for the whole group)

Open `kville-scheduler.html` in any browser — no install needed.

To sync across all 12 members' devices, add your Firebase config at the top of the file:

```js
const FIREBASE_CONFIG = {
  apiKey: "...",
  authDomain: "...",
  databaseURL: "...",
  projectId: "...",
  // ...
};
```

Leave it as `null` to use browser localStorage (single device only).

### 2. Python CLI (for the scheduler / admin)

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt --break-system-packages
```

**Commands:**

| Command | What it does |
|---|---|
| `python kville_schedule.py generate` | Generate schedule for the current week |
| `python kville_schedule.py generate --week 2026-01-19` | Generate for a specific week |
| `python kville_schedule.py show` | Print the current week's schedule |
| `python kville_schedule.py gaps` | List slots below required headcount |
| `python kville_schedule.py fairness` | Show hours distribution |
| `python kville_schedule.py phase` | Show current phase |
| `python kville_schedule.py phase --set blue` | Change phase (black / blue / white) |
| `python kville_schedule.py grace --weather 3` | Trigger 3-hour weather grace now |
| `python kville_schedule.py grace --list` | List all grace periods |
| `python kville_schedule.py trades` | List open trades |
| `python kville_schedule.py trades --accept <id> --as-member m3` | Accept a trade |
| `python kville_schedule.py pchecks` | Show P-Check status |
| `python kville_schedule.py pchecks --set "Alice" 3` | Record 3 checks for Alice |

## Setup

### 1. Edit the member roster

Open `data/members.json` and replace `"Member 1"` through `"Member 12"` with real names. Don't change the `id` values (`m1`–`m12`) — they're referenced throughout the data files.

### 2. Set the tenting phase

```bash
python kville_schedule.py phase --set blue
```

Or edit `"current_phase"` in `data/settings.json`.

### 3. Add games

Edit `data/settings.json` → `games` array:

```json
{
  "id": "unc_2026",
  "opponent": "UNC",
  "date": "2026-02-06",
  "time": "21:00",
  "is_home": true
}
```

Grace periods (2h buffer for home, 1h for away) are applied automatically.

### 4. Collect availability

Members fill out the availability grid in the browser app (`kville-scheduler.html`). If using the CLI only, edit `data/availability.json` directly using slot keys in `YYYY-MM-DD-HH` format and values `"green"`, `"yellow"`, or `"red"`.

### 5. Generate the schedule

```bash
python kville_schedule.py generate
python kville_schedule.py show
```

## Phase headcount rules

| Phase | Day slots (7 AM – 2:30 AM) | Night slots (2:30–7 AM) |
|---|---|---|
| Black Tenting | 2 members | 10 members |
| Blue Tenting | 1 member | 6 members |
| White / Flex | 1 member | 2 members |

## Running tests

```bash
pytest tests/ -v
```

## Project structure

```
kville/          Python package (models, scheduler, grace, storage)
kville_schedule.py   CLI entry point
data/            JSON data files (gitignored by default except settings.json)
tests/           pytest unit tests
kville-scheduler.html   Single-file browser app
```

See `CLAUDE.md` for developer/AI context.
