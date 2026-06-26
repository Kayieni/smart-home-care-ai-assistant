"""
Full Pipeline — The Invisible Caregiver
----------------------------------------
Orchestrates all three components in sequence for a demo run:

  Phase 1 — Simulator  : replay a chosen scenario timeline (MQTT + SQLite)
  Phase 2 — Auditor    : run hourly safety checks and write alerts.json
  Phase 3 — Narrator   : generate caregiver report from stored events + alerts

Each component can also be run independently:
  python run_simulator.py        — simulation only
  python run_auditor.py          — audit only (--simulated / --live)
  python run_narrator.py         — narrative report only

Usage:
    python run_simulation.py
"""

import datetime
from simulator.timeline import run_timeline, TIMELINE_NORMAL, TIMELINE_DECLINE, TIMELINE_HAZARD
from ai.safety_auditor import run_full_day_audit
from ai.narrator import run_narrator

SCENARIOS = {
    "1": ("Normal Day",   TIMELINE_NORMAL),
    "2": ("Decline Day",  TIMELINE_DECLINE),
    "3": ("Hazard Day",   TIMELINE_HAZARD),
}


def main():
    print("=" * 50)
    print("  THE INVISIBLE CAREGIVER — Full Pipeline")
    print("=" * 50)
    print()
    print("Choose scenario:")
    print("  1 — Normal Day     (healthy routine)")
    print("  2 — Decline Day    (missed medication, low activity)")
    print("  3 — Hazard Day     (stove unattended, resident left home)")
    print()

    choice = input("> ").strip()

    if choice not in SCENARIOS:
        print("Invalid choice. Please enter 1, 2, or 3.")
        return

    label, timeline = SCENARIOS[choice]
    today = datetime.date.today().isoformat()

    print()
    print(f"Running: {label}")
    print("-" * 50)

    # ── Phase 1: Simulator ───────────────────────────────────────────────────
    print("\n[Phase 1/3] Simulator — publishing events to MQTT + SQLite...")
    run_timeline(timeline, label)

    # ── Phase 2: Safety Auditor ───────────────────────────────────────────────
    print("\n[Phase 2/3] Safety Auditor — running hourly window analysis...")
    run_full_day_audit(today)

    # ── Phase 3: Narrator ────────────────────────────────────────────────────
    print("\n[Phase 3/3] Narrator — generating caregiver report...")
    run_narrator(today)


if __name__ == "__main__":
    main()
