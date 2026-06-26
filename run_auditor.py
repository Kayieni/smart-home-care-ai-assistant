"""
Safety Auditor — The Invisible Caregiver
-----------------------------------------
Phase 2 of the pipeline: run hourly safety checks against stored events.

Reads sensor events from data/events.db, applies Python rules + LLM layer,
and writes alerts to data/alerts.json.

Modes
-----
  --simulated [YYYY-MM-DD]   Replay every hour for a stored day (default: today).
                              Runs instantly — suitable for demos and testing.
  --live                     Poll in real time every 60 seconds.

Usage
-----
  python run_auditor.py                        # simulated, today's date
  python run_auditor.py --simulated 2026-06-26
  python run_auditor.py --live
"""

import sys
import time
import datetime
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai"))

from safety_auditor import run_audit, run_full_day_audit
from app_settings import POLL_INTERVAL_SECONDS, SIMULATED_START_HOUR, SIMULATED_END_HOUR


def _banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run_simulated(base_date: str):
    """Replay every hour 07:00–23:00 for base_date, then 00:00–05:00 next day."""
    _banner(f"Safety Auditor — SIMULATED  |  {base_date}")
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

    _banner(f"Done — {total_alerts} total alert(s) written to data/alerts.json")


def run_live():
    """Real-time mode: audit the current hour every POLL_INTERVAL_SECONDS."""
    _banner("Safety Auditor — LIVE  |  Press Ctrl+C to stop")
    print(f"Polling every {POLL_INTERVAL_SECONDS}s. Alerts appended to data/alerts.json.\n")

    seen_hours = set()
    try:
        while True:
            now = datetime.datetime.now()
            anchor_ts = now.strftime("%Y-%m-%dT%H:00:00")
            if anchor_ts not in seen_hours:
                seen_hours.add(anchor_ts)
                print(f"[{now.strftime('%H:%M:%S')}] Auditing {anchor_ts[11:16]}...", end=" ", flush=True)
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
        print("\n\nAuditor stopped.")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--live" in args:
        run_live()
    else:
        date_arg = None
        if "--simulated" in args:
            idx = args.index("--simulated")
            if idx + 1 < len(args):
                date_arg = args[idx + 1]
        if date_arg is None:
            date_arg = datetime.date.today().isoformat()
        run_simulated(date_arg)
