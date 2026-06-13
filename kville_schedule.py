#!/usr/bin/env python3
"""
kville_schedule.py
==================
Command-line interface for the K-Ville Tent Scheduler.

Usage
-----
  python kville_schedule.py generate              # generate schedule for current week
  python kville_schedule.py generate --week 2026-01-19
  python kville_schedule.py show                  # print current week's schedule
  python kville_schedule.py show --week 2026-01-19
  python kville_schedule.py gaps                  # list slots below required headcount
  python kville_schedule.py fairness              # print hours-per-member fairness report
  python kville_schedule.py phase --set blue      # change active tenting phase
  python kville_schedule.py grace --weather 3     # trigger 3-hour weather grace now
  python kville_schedule.py grace --list          # list all active grace periods
  python kville_schedule.py trades --list         # list open trades
  python kville_schedule.py trades --accept <id>  # accept a trade (updates schedule)
  python kville_schedule.py pchecks               # show P-Check status for all members
  python kville_schedule.py pchecks --set <name> <count>
"""

import argparse
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# Allow running from project root without installing the package
sys.path.insert(0, str(Path(__file__).parent))

from kville import (
    load_all, save_all, save_schedule, save_settings, save_trades,
    generate_schedule, fairness_report, coverage_gaps,
    get_week_start, is_night_slot, slot_key, parse_slot_key,
    grace_weather, PHASES,
)
from kville.models import Member


# ── Formatting helpers ────────────────────────────────────────

DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

def fmt_hour(h: int) -> str:
    if h == 0:   return "12 AM"
    if h < 12:   return f" {h} AM"
    if h == 12:  return "12 PM"
    return f" {h - 12} PM"

def fmt_slot(key: str) -> str:
    dt, hour = parse_slot_key(key)
    tag = "🌙" if is_night_slot(hour) else "☀ "
    return f"{DAYS[dt.weekday()]} {dt.month}/{dt.day} {fmt_hour(hour)} {tag}"

def member_name(members: list[Member], mid: str) -> str:
    m = next((m for m in members if m.id == mid), None)
    return m.name if m else mid

def parse_week(week_str: str | None) -> datetime:
    if week_str:
        d = datetime.strptime(week_str, "%Y-%m-%d")
    else:
        d = datetime.today()
    return get_week_start(d)


# ── Sub-commands ──────────────────────────────────────────────

def cmd_generate(args, data: dict) -> None:
    week_start = parse_week(args.week)
    print(f"Generating schedule for week of {week_start.strftime('%Y-%m-%d')} …")
    new_sched = generate_schedule(
        week_start,
        data["members"],
        data["availability"],
        data["settings"],
        existing=data["schedule"],
    )
    data["schedule"].update(new_sched)
    save_schedule(data["schedule"])

    gaps = coverage_gaps(new_sched, data["settings"], week_start)
    phase = PHASES[data["settings"].current_phase]
    print(f"Phase: {phase.label}  (day ≥{phase.day_required}, night ≥{phase.night_required})")
    print(f"Slots generated. Coverage gaps: {len(gaps)}")
    if gaps:
        print("  Unfilled slots:")
        for key in gaps:
            print(f"    {fmt_slot(key)}")
    print("Schedule saved.")


def cmd_show(args, data: dict) -> None:
    week_start = parse_week(args.week)
    schedule   = data["schedule"]
    members    = data["members"]
    settings   = data["settings"]
    phase      = PHASES[settings.current_phase]

    print(f"\n{'─'*60}")
    print(f"  K-Ville Schedule  |  Week of {week_start.strftime('%b %d, %Y')}")
    print(f"  Phase: {phase.label}  (day ≥{phase.day_required}, night ≥{phase.night_required})")
    print(f"{'─'*60}")

    for day_offset in range(7):
        day = week_start + timedelta(days=day_offset)
        day_slots = []
        for hour in range(0, 24, 2):
            key      = slot_key(day, hour)
            assigned = schedule.get(key, [])
            if assigned:
                day_slots.append((hour, assigned))
        if not day_slots:
            continue
        print(f"\n  {DAYS[day.weekday()]} {day.month}/{day.day}")
        for hour, assigned in day_slots:
            names = ", ".join(member_name(members, mid) for mid in assigned)
            tag   = "🌙" if is_night_slot(hour) else "☀ "
            print(f"    {tag} {fmt_hour(hour)}: {names}")
    print(f"\n{'─'*60}\n")


def cmd_gaps(args, data: dict) -> None:
    week_start = parse_week(args.week)
    gaps = coverage_gaps(data["schedule"], data["settings"], week_start)
    if not gaps:
        print("No coverage gaps — all slots are fully staffed.")
        return
    print(f"{len(gaps)} slot(s) below required headcount:")
    for key in gaps:
        assigned = data["schedule"].get(key, [])
        from kville.scheduler import required_count
        req = required_count(parse_slot_key(key)[1], data["settings"].current_phase)
        print(f"  {fmt_slot(key)}  {len(assigned)}/{req} assigned")


def cmd_fairness(args, data: dict) -> None:
    report = fairness_report(data["schedule"], data["members"])
    print(f"\n  Hours Distribution  (avg {report['average_hours']}h)")
    print(f"  {'Name':<20} {'Hours':>6}  {'Diff':>6}")
    print(f"  {'─'*20} {'─'*6}  {'─'*6}")
    for r in report["members"]:
        flag = " ⚠" if r["flag"] else ""
        diff_str = f"+{r['diff']}" if r["diff"] > 0 else str(r["diff"])
        print(f"  {r['name']:<20} {r['hours']:>5}h  {diff_str:>6}{flag}")
    print()


def cmd_phase(args, data: dict) -> None:
    if args.set:
        key = args.set.lower()
        if key not in PHASES:
            print(f"Unknown phase '{key}'. Choose: black, blue, white")
            sys.exit(1)
        data["settings"].current_phase = key
        save_settings(data["settings"])
        print(f"Phase set to: {PHASES[key].label}")
    else:
        p = PHASES[data["settings"].current_phase]
        print(f"Current phase: {p.label}")
        print(f"  Day requirement (7 AM – 2:30 AM): {p.day_required} member(s)")
        print(f"  Night requirement (2:30–7 AM):    {p.night_required} member(s)")


def cmd_grace(args, data: dict) -> None:
    settings = data["settings"]

    if args.weather is not None:
        gp = grace_weather(datetime.now(), hours=int(args.weather))
        settings.grace_periods.append(gp)
        save_settings(settings)
        print(f"Weather grace activated: {int(args.weather)}h from now.")
        print(f"  Ends: {datetime.fromisoformat(gp.end).strftime('%b %d %H:%M')}")
        return

    if args.list:
        gps = settings.grace_periods
        if not gps:
            print("No grace periods configured.")
            return
        now = datetime.now()
        print(f"\n  {'Status':<10} {'Reason':<40} {'Start':<18} {'End'}")
        print(f"  {'─'*10} {'─'*40} {'─'*18} {'─'*18}")
        for gp in gps:
            s = datetime.fromisoformat(gp.start)
            e = datetime.fromisoformat(gp.end)
            if now < s:   status = "upcoming"
            elif now > e: status = "past"
            else:         status = "ACTIVE"
            print(f"  {status:<10} {gp.reason[:40]:<40} {s.strftime('%m/%d %H:%M'):<18} {e.strftime('%m/%d %H:%M')}")
        print()
        return

    print("Specify --weather <hours> or --list")


def cmd_trades(args, data: dict) -> None:
    trades  = data["trades"]
    members = data["members"]

    if args.accept:
        trade = next((t for t in trades if t.id == args.accept), None)
        if not trade:
            print(f"Trade '{args.accept}' not found.")
            sys.exit(1)
        if trade.status != "open":
            print("That trade is already closed.")
            sys.exit(1)
        acceptor_id = args.as_member
        if not acceptor_id:
            print("Specify --as-member <member_id> to accept a trade.")
            sys.exit(1)
        # Swap in schedule
        sched = data["schedule"]
        slot  = sched.get(trade.slot_key, [])
        slot  = [mid for mid in slot if mid != trade.poster_id]
        if acceptor_id not in slot:
            slot.append(acceptor_id)
        sched[trade.slot_key] = slot
        save_schedule(sched)
        # Mark trade accepted
        trade.status      = "accepted"
        trade.acceptor_id = acceptor_id
        trade.accepted_ts = datetime.now().timestamp()
        save_trades(trades)
        print(f"Trade accepted. {fmt_slot(trade.slot_key)} now assigned to "
              f"{member_name(members, acceptor_id)}.")
        return

    # Default: list open trades
    open_trades = [t for t in trades if t.status == "open"]
    if not open_trades:
        print("No open trades.")
        return
    print(f"\n  Open Trades ({len(open_trades)})")
    print(f"  {'ID':<25} {'Slot':<30} {'Posted by':<20} Note")
    print(f"  {'─'*25} {'─'*30} {'─'*20} {'─'*20}")
    for t in open_trades:
        print(f"  {t.id:<25} {fmt_slot(t.slot_key):<30} "
              f"{member_name(members, t.poster_id):<20} {t.note}")
    print()


def cmd_pchecks(args, data: dict) -> None:
    settings = data["settings"]
    members  = data["members"]

    if args.set:
        name, count_str = args.set
        count = int(count_str)
        m = next((m for m in members if m.name.lower() == name.lower()), None)
        if not m:
            m = next((m for m in members if m.id == name), None)
        if not m:
            print(f"Member '{name}' not found.")
            sys.exit(1)
        settings.pchecks[m.id] = count
        save_settings(settings)
        status = "✓ wristband" if count >= 3 else f"needs {3 - count} more"
        print(f"{m.name}: {count}/5 checks — {status}")
        return

    print(f"\n  P-Check Status  (need 3 of 5 for wristband)")
    print(f"  {'Name':<22} {'Checks':>7}  Status")
    print(f"  {'─'*22} {'─'*7}  {'─'*20}")
    for m in members:
        c      = settings.pchecks.get(m.id, 0)
        status = "✓ WRISTBAND" if c >= 3 else f"need {3 - c} more"
        print(f"  {m.name:<22} {c:>4}/5    {status}")
    print()


# ── Argument parser ───────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kville_schedule",
        description="K-Ville Tent Scheduler CLI",
    )
    sub = p.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Generate schedule for a week")
    gen.add_argument("--week", help="Week start date YYYY-MM-DD (default: current week)")

    show = sub.add_parser("show", help="Print schedule for a week")
    show.add_argument("--week", help="Week start date YYYY-MM-DD")

    gaps = sub.add_parser("gaps", help="List slots below required headcount")
    gaps.add_argument("--week", help="Week start date YYYY-MM-DD")

    sub.add_parser("fairness", help="Show hours distribution across members")

    ph = sub.add_parser("phase", help="View or change tenting phase")
    ph.add_argument("--set", choices=["black", "blue", "white"],
                    help="Set the active phase")

    gr = sub.add_parser("grace", help="Manage grace periods")
    gr.add_argument("--weather", metavar="HOURS", help="Trigger weather grace for N hours")
    gr.add_argument("--list", action="store_true", help="List all grace periods")

    tr = sub.add_parser("trades", help="View or accept trades")
    tr.add_argument("--list", action="store_true", help="List open trades (default)")
    tr.add_argument("--accept", metavar="TRADE_ID", help="Accept a trade by ID")
    tr.add_argument("--as-member", metavar="MEMBER_ID", help="Member accepting the trade")

    pc = sub.add_parser("pchecks", help="View or update P-Check counts")
    pc.add_argument("--set", nargs=2, metavar=("NAME", "COUNT"),
                    help="Set check count for a member")

    return p


# ── Entry point ───────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    data = load_all()

    dispatch = {
        "generate": cmd_generate,
        "show":     cmd_show,
        "gaps":     cmd_gaps,
        "fairness": cmd_fairness,
        "phase":    cmd_phase,
        "grace":    cmd_grace,
        "trades":   cmd_trades,
        "pchecks":  cmd_pchecks,
    }

    fn = dispatch.get(args.command)
    if fn:
        fn(args, data)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
