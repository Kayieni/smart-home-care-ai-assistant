"""
Safety Auditor — Scheduled Loop
---------------------------------
Satisfies the coursework requirement:
  "Runs as a cron-job or loop every 60 minutes."

Modes
-----
  --simulated   Replay a stored day hour-by-hour using simulated timestamps.
                Each iteration runs instantly (no real-time wait).
                Useful for demonstrating the auditor against a recorded scenario.

  --live        Run in real time: audit the CURRENT hour every 60 real seconds.
                This is the production/demo mode for a continuously running system.

Usage
-----
  python run_auditor_loop.py                   # simulated mode, today's date
  python run_auditor_loop.py --simulated 2026-06-17
  python run_auditor_loop.py --live
"""

import sys
import time
import datetime

# ---------------------------------------------------------------------------
# Path fix so this script can be run from the project root without installing
# ---------------------------------------------------------------------------
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai"))

from safety_auditor import run_audit
from app_settings import POLL_INTERVAL_SECONDS, SIMULATED_START_HOUR, SIMULATED_END_HOUR


def _banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run_simulated(base_date: str):
    """
    Replay every hour from 07:00 to 23:00 for the given date,
    then 00:00 to 05:00 of the following day (catches night-time exits).
    Runs immediately (no sleep) — suitable for demos and testing.
    """
    _banner(f"Safety Auditor — SIMULATED mode  |  date: {base_date}")
    print("Iterating through each hour checkpoint...\n")

    next_date = (datetime.date.fromisoformat(base_date) + datetime.timedelta(days=1)).isoformat()

    checkpoints = (
        [(base_date, h) for h in range(SIMULATED_START_HOUR, SIMULATED_END_HOUR + 1)]
        + [(next_date, h) for h in range(0, 6)]
    )

    total_alerts = 0
    for date, hour in checkpoints:
        anchor_ts = f"{date}T{hour:02d}:00:00"
        label = anchor_ts[11:16] + (" (next day)" if date == next_date else "")
        print(f"[{label}] Running audit...", end=" ", flush=True)
        alerts = run_audit(anchor_ts)
        if alerts:
            print(f"{len(alerts)} alert(s):")
            for a in alerts:
                print(f"         [{a['severity'].upper()}] {a['risk']}: {a['reason']}")
        else:
            print("no alerts.")
        total_alerts += len(alerts)

    _banner(f"Simulation complete — {total_alerts} total alert(s) generated.")


def run_live():
    """
    Real-time mode: audit the current hour every POLL_INTERVAL_SECONDS seconds.
    Runs until interrupted with Ctrl+C.
    """
    _banner("Safety Auditor — LIVE mode  |  Press Ctrl+C to stop")
    print(f"Checking every {POLL_INTERVAL_SECONDS}s. Alerts are appended to data/alerts.json.\n")

    seen_hours = set()

    try:
        while True:
            now = datetime.datetime.now()
            anchor_ts = now.strftime("%Y-%m-%dT%H:00:00")

            if anchor_ts not in seen_hours:
                seen_hours.add(anchor_ts)
                print(f"[{now.strftime('%H:%M:%S')}] Running audit for hour window ending {anchor_ts[11:16]}...",
                      end=" ", flush=True)
                alerts = run_audit(anchor_ts)
                if alerts:
                    print(f"{len(alerts)} alert(s):")
                    for a in alerts:
                        print(f"         [{a['severity'].upper()}] {a['risk']}: {a['reason']}")
                else:
                    print("no alerts.")
            else:
                print(f"[{now.strftime('%H:%M:%S')}] Waiting for next hour...", end="\r", flush=True)

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\nAuditor loop stopped.")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--live" in args:
        run_live()
    else:
        # Default: simulated mode
        # Optional: pass a date as second argument, e.g. --simulated 2026-06-17
        date_arg = None
        if "--simulated" in args:
            idx = args.index("--simulated")
            if idx + 1 < len(args):
                date_arg = args[idx + 1]

        if date_arg is None:
            date_arg = datetime.date.today().isoformat()

        run_simulated(date_arg)
