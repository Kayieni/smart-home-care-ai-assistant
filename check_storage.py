import datetime
from ai.safety_auditor import run_full_day_audit

today = datetime.date.today().isoformat()

print(f"=== Safety Audit: {today} ===\n")
alerts = run_full_day_audit(today)

print(f"\nTotal alerts: {len(alerts)}")
if not alerts:
    print("No safety concerns detected.")

