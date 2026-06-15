# K-Ville Tent Scheduler

A scheduling and coordination tool for Duke Basketball K-Ville tenting groups. Twelve members manage tent shifts, availability, trades, and P-Check attendance through a shared web app — no installs required.

**Live app:** [fanciful-kitten-d08ed5.netlify.app](https://fanciful-kitten-d08ed5.netlify.app)
**Repo:** [github.com/maryclaytonsoto/kville-scheduler](https://github.com/maryclaytonsoto/kville-scheduler)

---

## What it does

- **Group codes** — each tent group creates or joins a 6-character code; all data is isolated per group
- **Availability input** — members mark each 2-hour slot green / yellow / red on a weekly grid
- **Auto-schedule** — generates a fair schedule respecting headcount rules for the current phase
- **Grace periods** — auto-blocks game windows (2h home, 1h away), weather graces, and post-check windows
- **Trade board** — post a shift, accept someone else's; schedule updates instantly
- **P-Check tracking** — records wristband check attendance (need 3 of 5 to earn a wristband)
- **Stick-figure roster** — photo avatars with bobblehead proportions, shown on the dashboard and member list
- **Fairness reporting** — flags members >4h over or under the group average

---

## Getting started

### Option 1: Use the live site (recommended)

Open [fanciful-kitten-d08ed5.netlify.app](https://fanciful-kitten-d08ed5.netlify.app) on any device.

- **Team captain**: click "Create Group" → share the 6-character code with your group
- **Everyone else**: click "Join Group" → enter the code → pick your name

Data syncs in real time across all members' devices via Firebase.

### Option 2: Run locally (single device, no sync)

Download `index.html` and open it in any browser. Data is stored in localStorage only.

---

## Phase headcount rules

| Phase | Day slots (7 AM – 2:30 AM) | Night slots (2:30–7 AM) |
|---|---|---|
| Black Tenting | 2 members | 10 members |
| Blue Tenting | 1 member | 6 members |
| White / Flex | 1 member | 2 members |

The app uses the current phase to calculate required occupancy when generating schedules and displaying the dashboard status.

---

## Firebase setup (for self-hosting)

The live site uses a shared Firebase project. To run your own instance:

1. Create a [Firebase](https://console.firebase.google.com) project and enable Realtime Database (test mode)
2. Register a web app and copy the config object
3. Open `index.html` and replace the `FIREBASE_CONFIG` value near the top:

```js
const FIREBASE_CONFIG = {
  apiKey: "...",
  authDomain: "...",
  databaseURL: "...",
  projectId: "...",
  storageBucket: "...",
  messagingSenderId: "...",
  appId: "..."
};
```

Leave as `null` to use localStorage only (single device, no sync).

---

## Deploying your own copy

1. Fork this repo on GitHub
2. Go to [netlify.com](https://netlify.com) → "Add new site" → "Import from Git"
3. Connect your forked repo — Netlify auto-detects `index.html` and deploys immediately
4. Push any change to `main` to trigger a redeploy

---

## Python CLI (admin / schedule generation)

A Python package is included for schedule generation and data management from the command line.

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt --break-system-packages
```

### Commands

| Command | What it does |
|---|---|
| `python kville_schedule.py generate` | Generate schedule for the current week |
| `python kville_schedule.py generate --week 2026-01-19` | Generate for a specific week |
| `python kville_schedule.py show` | Print the current week's schedule |
| `python kville_schedule.py gaps` | List slots below required headcount |
| `python kville_schedule.py fairness` | Show hours distribution (⚠ = >4h from average) |
| `python kville_schedule.py phase` | Show current phase |
| `python kville_schedule.py phase --set blue` | Change phase (black / blue / white) |
| `python kville_schedule.py grace --weather 3` | Trigger 3-hour weather grace now |
| `python kville_schedule.py grace --list` | List all grace periods |
| `python kville_schedule.py trades` | List open trades |
| `python kville_schedule.py trades --accept <id> --as-member m3` | Accept a trade |
| `python kville_schedule.py pchecks` | Show P-Check status |
| `python kville_schedule.py pchecks --set "Alice" 3` | Record 3 checks for Alice |

### Data setup

**Edit the roster** — open `data/members.json` and replace `"Member 1"` through `"Member 12"` with real names. Don't change the `id` values (`m1`–`m12`).

**Set the phase** — `python kville_schedule.py phase --set blue`

**Add games** — edit `data/settings.json` → `games` array:
```json
{
  "id": "unc_2026",
  "opponent": "UNC",
  "date": "2026-02-06",
  "time": "21:00",
  "is_home": true
}
```
Grace periods (2h for home, 1h for away) are applied automatically.

### Running tests

```bash
pytest tests/ -v
```

---

## Project structure

```
index.html              Single-file browser app (React 18 + Tailwind + Firebase)
kville_schedule.py      CLI entry point
kville/                 Python package (models, scheduler, grace, storage)
data/                   JSON data files
tests/                  pytest unit tests
CLAUDE.md               Developer / AI assistant context
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 (Babel Standalone — no build step), Tailwind CSS CDN |
| Fonts | Playfair Display (headings), Inter (body) via Google Fonts |
| Sync | Firebase Realtime Database (compat SDK v9) |
| Hosting | Netlify (auto-deploy from GitHub) |
| Backend / CLI | Python 3.10+, no external runtime |

See `CLAUDE.md` for full developer and AI assistant context.
