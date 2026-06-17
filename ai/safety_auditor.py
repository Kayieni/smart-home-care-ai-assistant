"""
Safety Auditor
--------------
Runs at each simulated hour checkpoint.
Queries the 1h event window and produces structured JSON alerts.
"""

import json
import os
from datetime import datetime
from ai.storage import get_window, get_latest_sensor_states

ALERTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "alerts.json")

# Inactivity alert threshold: no motion in this many hours triggers alert
INACTIVITY_THRESHOLD_HOURS = 3


def _load_alerts() -> list:
    if os.path.exists(ALERTS_PATH):
        with open(ALERTS_PATH, "r") as f:
            return json.load(f)
    return []


def _save_alerts(alerts: list):
    os.makedirs(os.path.dirname(ALERTS_PATH), exist_ok=True)
    with open(ALERTS_PATH, "w") as f:
        json.dump(alerts, f, indent=2)


def _make_alert(anchor_ts: str, risk: str, severity: str, reason: str) -> dict:
    return {
        "timestamp": anchor_ts,
        "risk": risk,
        "severity": severity,
        "reason": reason
    }


def run_audit(anchor_ts: str) -> list:
    """
    Run a safety audit for the 1h window ending at anchor_ts.
    Returns a list of alert dicts and appends them to alerts.json.

    anchor_ts: ISO string, e.g. "2026-06-17T09:00:00"
    """
    window_events = get_window(anchor_ts, hours=1)
    state = get_latest_sensor_states(window_events)

    # Also look back further for inactivity check
    # Any sensor firing counts as evidence the resident is present and active
    long_window = get_window(anchor_ts, hours=INACTIVITY_THRESHOLD_HOURS)
    activity_sensors = {
        "BEDROOM_PIR_01", "KITCHEN_PIR_01", "HALLWAY_PIR_01",
        "BATH_WATER_01", "FRIDGE_DOOR_01", "STOVE_POWER_01",
        "MED_BOX_01", "SOAP_VIB_01", "DOOR_CONTACT_01"
    }
    any_motion = any(e["sensor_id"] in activity_sensors for e in long_window)

    alerts = []
    hour = datetime.fromisoformat(anchor_ts).hour

    # --- RULE 1: Stove left on ---
    if state.get("STOVE_POWER_01") == "on":
        alerts.append(_make_alert(anchor_ts, "stove_on",
            "high",
            f"Stove is still ON at {anchor_ts[11:16]}. No off event detected in the last hour."))

    # --- RULE 2: Stove on + door opened (left home while cooking) ---
    if state.get("STOVE_POWER_01") == "on" and state.get("DOOR_CONTACT_01") == "open":
        alerts.append(_make_alert(anchor_ts, "stove_unattended",
            "critical",
            "Stove is ON and front door was opened. Resident may have left home while cooking."))

    # --- RULE 3: Medication not taken by 10:00 ---
    if hour >= 10 and state.get("MED_BOX_01") == "not_used":
        alerts.append(_make_alert(anchor_ts, "medication_missed",
            "medium",
            f"Medication box not interacted with by {anchor_ts[11:16]}."))

    # --- RULE 4: No motion detected for 3+ hours during daytime ---
    if 9 <= hour <= 21 and not any_motion:
        alerts.append(_make_alert(anchor_ts, "inactivity",
            "medium",
            f"No movement detected in {INACTIVITY_THRESHOLD_HOURS} hours ending at {anchor_ts[11:16]}."))

    # --- RULE 5: Night exit (door opened between 23:00–05:00) ---
    if (hour >= 23 or hour <= 5) and state.get("DOOR_CONTACT_01") == "open":
        alerts.append(_make_alert(anchor_ts, "night_exit",
            "high",
            f"Front door opened at {anchor_ts[11:16]}. Unusual night-time exit detected."))

    # Persist alerts
    if alerts:
        existing = _load_alerts()
        existing.extend(alerts)
        _save_alerts(existing)

    return alerts


def run_full_day_audit(base_date: str) -> list:
    """
    Run audits at every hour checkpoint from 07:00 to 23:00.
    base_date: YYYY-MM-DD string
    """
    all_alerts = []

    # Clear previous alerts for this run
    _save_alerts([])

    for hour in range(7, 24):
        anchor_ts = f"{base_date}T{hour:02d}:00:00"
        alerts = run_audit(anchor_ts)
        if alerts:
            for a in alerts:
                print(f"  [{a['severity'].upper()}] {a['risk']} @ {anchor_ts[11:16]}: {a['reason']}")
        all_alerts.extend(alerts)

    return all_alerts
