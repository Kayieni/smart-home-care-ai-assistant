"""
Narrator — The Invisible Caregiver
-------------------------------------
Phase 3 of the pipeline: generate caregiver report and Q&A session.

Reads sensor events from data/events.db and alerts from data/alerts.json.
Produces a structured daily summary (JSON) and a human-readable report via LLM.

Prerequisites: run the Simulator and Safety Auditor first.
    python run_simulator.py
    python run_auditor.py --simulated <YYYY-MM-DD>

Usage:
    python run_narrator.py                     # today's date, report only
    python run_narrator.py --date 2026-06-26   # specific date
    python run_narrator.py --qa                # report + interactive Q&A loop
"""

import sys
import datetime
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai"))

from narrator import run_narrator, caregiver_qa_loop


def main():
    args = sys.argv[1:]

    date_arg = None
    if "--date" in args:
        idx = args.index("--date")
        if idx + 1 < len(args):
            date_arg = args[idx + 1]
    if date_arg is None:
        date_arg = datetime.date.today().isoformat()

    qa_mode = "--qa" in args

    print("=" * 50)
    print("  THE INVISIBLE CAREGIVER — Narrator")
    print("=" * 50)

    if qa_mode:
        caregiver_qa_loop(date_arg)
    else:
        run_narrator(date_arg)


if __name__ == "__main__":
    main()
