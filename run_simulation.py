"""
Full System Integration — The Invisible Caregiver
--------------------------------------------------
Single entry point that runs the complete pipeline:

  1. Choose a scenario
  2. Simulate a full-day timeline (MQTT + local storage)
  3. Run the Safety Auditor (hourly window analysis)
  4. Run the Narrator AI (24h summary + caregiver report)

Usage:
    python run_simulation.py
"""

import datetime
from simulator.timeline import run_timeline, TIMELINE_NORMAL, TIMELINE_DECLINE, TIMELINE_HAZARD
from ai.narrator import run_narrator

SCENARIOS = {
    "1": ("Normal Day",   TIMELINE_NORMAL),
    "2": ("Decline Day",  TIMELINE_DECLINE),
    "3": ("Hazard Day",   TIMELINE_HAZARD),
}


def main():
    print("=" * 50)
    print("  THE INVISIBLE CAREGIVER")
    print("  Smart Home Elderly Care Simulation")
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

    print()
    print(f"Running: {label}")
    print("-" * 50)

    # PHASE 1: Simulate and store
    run_timeline(timeline, label)

    # PHASE 2: Audit + Narrate
    today = datetime.date.today().isoformat()
    run_narrator(today)


if __name__ == "__main__":
    main()
