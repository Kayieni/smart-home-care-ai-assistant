"""
Narrator AI Pipeline
--------------------
Takes the 24h event log and safety alerts.
Produces:
  1. A structured activity summary (JSON)
  2. A human-readable caregiver report (via LLM or template)
"""

import json
import datetime
from ai.storage import get_all_events_today
from ai.safety_auditor import run_full_day_audit
from ai.llm_reporter import generate_report


def _detect_activities_from_day(events: list) -> list:
    """
    Detects activities by checking whether key sensor values
    occurred AT ANY POINT during the day — not just the final state.
    This is more accurate for daily summaries than a snapshot.
    """
    # Build a set of (sensor_id, value) pairs seen during the day
    seen = {(e["sensor_id"], e["value"]) for e in events}

    activities = []

    if ("BED_PRESSURE_01", "empty") in seen:
        activities.append("wake_up")

    if ("BATH_WATER_01", "flow") in seen and ("SOAP_VIB_01", "used") in seen:
        activities.append("hygiene")

    if ("FRIDGE_DOOR_01", "open") in seen:
        activities.append("eating")

    if ("MED_BOX_01", "used") in seen:
        activities.append("medication_taken")

    if ("STOVE_POWER_01", "on") in seen:
        activities.append("cooking_risk")

    if ("DOOR_CONTACT_01", "open") in seen:
        activities.append("leaving_home")

    return activities


def build_daily_summary(date: str) -> dict:
    """
    Builds a structured JSON summary of the day.
    date: YYYY-MM-DD string
    """
    events = get_all_events_today(date)
    alerts = run_full_day_audit(date)

    # Detect activities from all events seen during the day
    event_dicts = [{"sensor_id": e["sensor_id"], "value": e["value"]} for e in events]
    activities = _detect_activities_from_day(event_dicts)

    # Group alerts by severity
    critical = [a for a in alerts if a["severity"] == "critical"]
    high     = [a for a in alerts if a["severity"] == "high"]
    medium   = [a for a in alerts if a["severity"] == "medium"]

    # Build event timeline (human-readable)
    timeline = [
        {"time": e["simulated_ts"][11:16], "sensor": e["sensor_id"], "value": e["value"]}
        for e in events
    ]

    summary = {
        "date": date,
        "total_events": len(events),
        "activities_detected": activities,
        "alert_counts": {
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "total": len(alerts)
        },
        "alerts": alerts,
        "timeline": timeline
    }

    return summary


def run_narrator(date: str = None):
    """
    Full narrator pipeline:
    1. Build structured daily summary
    2. Generate caregiver report
    3. Print and save both outputs
    """
    if date is None:
        date = datetime.date.today().isoformat()

    print(f"\n=== Narrator AI — Daily Report: {date} ===\n")

    summary = build_daily_summary(date)

    # Print structured summary
    print("--- STRUCTURED SUMMARY (JSON) ---")
    print(json.dumps({
        "date": summary["date"],
        "activities_detected": summary["activities_detected"],
        "alert_counts": summary["alert_counts"],
    }, indent=2))

    # Derive risks list for LLM reporter (reuse existing format)
    risks = [
        {"risk": a["risk"], "severity": a["severity"], "reason": a["reason"]}
        for a in summary["alerts"]
    ]
    # Deduplicate by risk type
    seen = set()
    unique_risks = []
    for r in risks:
        if r["risk"] not in seen:
            seen.add(r["risk"])
            unique_risks.append(r)

    # Generate caregiver report
    print("\n--- CAREGIVER REPORT ---")
    report = generate_report(summary["activities_detected"], unique_risks)
    print(report)
    print("------------------------\n")

    # Save full summary to file
    import os
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data", f"summary_{date}.json"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Full summary saved to: data/summary_{date}.json")


if __name__ == "__main__":
    run_narrator()
