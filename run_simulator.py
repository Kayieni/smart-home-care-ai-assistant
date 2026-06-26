"""
Simulator — The Invisible Caregiver
-------------------------------------
Phase 1 of the pipeline: replay a scenario timeline.

Publishes every sensor event to ThingsBoard via MQTT and stores it in the
local SQLite database (data/events.db).  No analysis is performed here.

Run the Safety Auditor next:
    python run_auditor.py --simulated <YYYY-MM-DD>

Usage:
    python run_simulator.py              # interactive scenario selection
    python run_simulator.py --scenario 3 # non-interactive (1=Normal, 2=Decline, 3=Hazard)
"""

import sys
from simulator.timeline import run_timeline, TIMELINE_NORMAL, TIMELINE_DECLINE, TIMELINE_HAZARD

SCENARIOS = {
    "1": ("Normal Day",  TIMELINE_NORMAL),
    "2": ("Decline Day", TIMELINE_DECLINE),
    "3": ("Hazard Day",  TIMELINE_HAZARD),
}


def main():
    # Non-interactive mode: python run_simulator.py --scenario N
    args = sys.argv[1:]
    choice = None
    if "--scenario" in args:
        idx = args.index("--scenario")
        if idx + 1 < len(args):
            choice = args[idx + 1]

    if choice is None:
        print("=" * 50)
        print("  THE INVISIBLE CAREGIVER — Simulator")
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
        sys.exit(1)

    label, timeline = SCENARIOS[choice]
    print(f"\nRunning: {label}")
    print("-" * 50)
    run_timeline(timeline, label)


if __name__ == "__main__":
    main()
