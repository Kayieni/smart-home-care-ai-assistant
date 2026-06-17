"""
test_ai_pipeline.py
-------------------
Verifies the full AI pipeline: activity detection, safety audit, narrator report.
Run AFTER a simulation scenario to have data in the database.
Run from project root: python tests/test_ai_pipeline.py
"""

import datetime
from ai.storage import get_all_events_today
from ai.safety_auditor import run_full_day_audit
from ai.narrator import run_narrator

today = datetime.date.today().isoformat()

print("Testing AI pipeline...\n")

events = get_all_events_today(today)
print(f"  Events in DB for today: {len(events)}")
assert len(events) > 0, "No events found — run a simulation scenario first."

alerts = run_full_day_audit(today)
print(f"  Alerts generated: {len(alerts)}")

print("\n  Running narrator...")
run_narrator(today)

print("\nAI pipeline test passed.")
