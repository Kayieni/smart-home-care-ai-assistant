"""
Safety Auditor
--------------
Runs at each simulated hour checkpoint.
Queries the 1h event window and produces structured JSON alerts.

Two complementary layers:
  1. Rule-based (Python)  — deterministic, always runs
  2. LLM-based (Ollama)   — interprets events against the Care Plan,
                            falls back silently if Ollama is unavailable
"""

import json
import os
import requests
from datetime import datetime
from storage import get_window, get_latest_sensor_states
from app_settings import OLLAMA_URL, OLLAMA_MODEL, LLM_TIMEOUT, INACTIVITY_THRESHOLD_HOURS

ALERTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "alerts.json")
RULES_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "rules.json")


def _load_care_plan() -> dict:
    with open(RULES_PATH, "r") as f:
        return json.load(f).get("care_plan", {})


def _load_alerts() -> list:
    if os.path.exists(ALERTS_PATH):
        with open(ALERTS_PATH, "r") as f:
            return json.load(f)
    return []


def _save_alerts(alerts: list):
    os.makedirs(os.path.dirname(ALERTS_PATH), exist_ok=True)
    with open(ALERTS_PATH, "w") as f:
        json.dump(alerts, f, indent=2)


def load_alerts_for_date(date: str) -> list:
    """Return saved alerts for a specific date (YYYY-MM-DD) from alerts.json.
    The narrator calls this instead of re-running the full audit."""
    return [a for a in _load_alerts() if a.get("timestamp", "").startswith(date)]


def _make_alert(anchor_ts: str, risk: str, severity: str, reason: str) -> dict:
    return {
        "timestamp": anchor_ts,
        "risk": risk,
        "severity": severity,
        "reason": reason
    }


def _build_daily_status(anchor_ts: str, hour: int) -> str:
    """
    Returns a compact summary of what daily-level rules have already been
    satisfied from 07:00 up to anchor_ts.  Injected into the LLM prompt
    so it does not flag things that happened outside its 1-hour window.
    """
    day_events = get_window(anchor_ts, hours=max(1, hour - 6))

    med_taken    = any(e["sensor_id"] == "MED_BOX_01"          and e["value"] == "1" for e in day_events)
    toilet_used  = any(e["sensor_id"] == "TOILET_OCCUPANCY_01" and e["value"] == "1" for e in day_events)
    soap_used    = any(e["sensor_id"] == "SOAP_VIB_01"         and e["value"] == "1" for e in day_events)

    stove_events = [e for e in day_events if e["sensor_id"] == "STOVE_POWER_01"]
    if stove_events:
        last_stove = stove_events[-1]
        if last_stove["value"] == "1":
            stove_status = "ON (not yet turned off)"
        else:
            stove_status = f"OFF (turned off at {last_stove['simulated_ts'][11:16]})"
    else:
        stove_status = "not used today / OFF"

    lines = [
        f"  - Medication taken today (by {anchor_ts[11:16]}): {'YES' if med_taken else 'NO'}",
        f"  - Toilet used today:                              {'YES' if toilet_used else 'NO'}",
        f"  - Hand washing (soap) observed today:             {'YES' if soap_used else 'NO'}",
        f"  - Stove status right now:                         {stove_status}",
        f"  - Current hour: {hour:02d}:00  (medication deadline is 10:00)",
    ]
    return "\n".join(lines)


def _llm_audit(anchor_ts: str, window_events: list) -> list:
    """
    Sends the last 1h events + Care Plan to Ollama.
    Asks the LLM to identify rule violations and return structured JSON alerts.
    Falls back to an empty list if Ollama is unavailable or returns unparseable output.
    """
    # Skip LLM entirely for empty windows — nothing to evaluate
    if not window_events:
        return []

    hour = datetime.fromisoformat(anchor_ts).hour
    care_plan = _load_care_plan()
    rules_text = "\n".join(
        f"- [{r['id']}] ({r['priority'].upper()}) {r['description']}"
        for r in care_plan.get("rules", [])
    )
    from sensor_model_loader import decode_value
    events_text = "\n".join(
        f"  {e['simulated_ts'][11:16]}  {e['sensor_id']} = {decode_value(e['sensor_id'], e['value'])}"
        for e in window_events
    )

    from sensor_model_loader import sensor_context_for_prompt
    sensor_context = sensor_context_for_prompt()
    daily_status   = _build_daily_status(anchor_ts, hour)

    # Allowed risk keys — prevents inconsistent naming across hours
    allowed_risks = (
        "medication_missed, stove_on, stove_unattended, inactivity, night_exit, "
        "water_heater_on, fridge_left_open, no_handwash_after_toilet, no_toilet_use"
    )

    prompt = f"""You are an automated Safety Auditor for an elderly care smart home system.
Your job is to check whether the sensor events from the LAST 1 HOUR violate any Care Plan rule.

IMPORTANT CONTEXT — what has already happened today (do NOT re-flag these):
{daily_status}

SENSOR CATALOGUE:
{sensor_context}

CARE PLAN RULES:
{rules_text}

SENSOR EVENTS (last 1 hour ending at {anchor_ts[11:16]}):
{events_text}

INSTRUCTIONS:
- Only flag violations that are EVIDENT from the events above.
- Do NOT flag medication_missed before 10:00 AM.
- Do NOT flag medication_missed if the daily status shows "Medication taken today: YES".
- Do NOT flag toilet or handwash violations if the daily status shows they were already satisfied.
- Do NOT flag stove_on or stove_unattended unless STOVE_POWER_01=on explicitly appears in the 1-hour events listed above. If stove status is "OFF" in daily status, do NOT flag any stove issue.
- Do NOT flag fridge_left_open if both a FRIDGE_DOOR_01=open AND a FRIDGE_DOOR_01=closed event appear in the events above (it was opened and properly closed).
- Do NOT flag inactivity if the current hour is before 09:00.
- Do NOT flag no_toilet_use — this is checked only once at 21:00 by the rule engine, never hourly.
- Use ONLY these risk identifiers (exact spelling): {allowed_risks}
- If no rules are violated, return exactly: []

Return ONLY a JSON array. No prose, no markdown, no explanation outside the JSON.
Each object: {{"risk": "...", "severity": "...", "reason": "..."}}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=LLM_TIMEOUT
        )
        response.raise_for_status()
        raw = response.json()["response"].strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        llm_alerts = json.loads(raw)
        if not isinstance(llm_alerts, list):
            return []

        # Filter to only allowed risk keys; normalise severity to lowercase
        allowed = set(allowed_risks.replace(" ", "").split(","))
        return [
            _make_alert(anchor_ts, a.get("risk", ""), a.get("severity", "medium").lower(), a.get("reason", ""))
            for a in llm_alerts
            if isinstance(a, dict) and a.get("reason") and a.get("risk", "") in allowed
        ]
    except Exception:
        return []


def _post_filter_llm_alerts(alerts: list, anchor_ts: str, window_events: list) -> list:
    """
    Hard deterministic guard applied AFTER the LLM response.
    Strips hallucinated alerts that the prompt instructions alone cannot prevent.
    Each rule mirrors what the Python rule engine already enforces, so the LLM
    cannot contradict a deterministic check.
    """
    hour = datetime.fromisoformat(anchor_ts).hour

    # Window facts
    stove_on_in_window = any(
        e["sensor_id"] == "STOVE_POWER_01" and e["value"] == "1" for e in window_events
    )
    heater_evts = [e for e in window_events if e["sensor_id"] == "WATER_HEATER_01"]
    heater_currently_on = bool(heater_evts) and heater_evts[-1]["value"] == "1"

    fridge_evts = [e for e in window_events if e["sensor_id"] == "FRIDGE_DOOR_01"]
    fridge_open_unclosed = False
    if fridge_evts:
        f_opens  = [e for e in fridge_evts if e["value"] == "1"]
        f_closes = [e for e in fridge_evts if e["value"] == "0"]
        if f_opens:
            last_open  = datetime.fromisoformat(f_opens[-1]["simulated_ts"])
            last_close = datetime.fromisoformat(f_closes[-1]["simulated_ts"]) if f_closes else None
            fridge_open_unclosed = (last_close is None or last_close < last_open)

    door_opened_in_window = any(
        e["sensor_id"] == "DOOR_CONTACT_01" and e["value"] == "1" for e in window_events
    )
    toilet_cleared_in_window = any(
        e["sensor_id"] == "TOILET_OCCUPANCY_01" and e["value"] == "0" for e in window_events
    )

    # Re-compute inactivity fact (mirrors rule engine logic)
    from sensor_model_loader import ACTIVITY_SENSOR_IDS
    long_window = get_window(anchor_ts, hours=INACTIVITY_THRESHOLD_HOURS)
    any_motion  = any(e["sensor_id"] in ACTIVITY_SENSOR_IDS for e in long_window)

    # Day-wide facts
    lookback   = max(1, hour - 6)
    day_events = get_window(anchor_ts, hours=lookback)
    med_taken       = any(e["sensor_id"] == "MED_BOX_01"          and e["value"] == "1" for e in day_events)
    toilet_used_day = any(e["sensor_id"] == "TOILET_OCCUPANCY_01" and e["value"] == "1" for e in day_events)
    soap_used_day   = any(e["sensor_id"] == "SOAP_VIB_01"         and e["value"] == "1" for e in day_events)

    result = []
    for a in alerts:
        risk = a.get("risk", "")

        # Inactivity: only valid 09:00–21:00, and only if motion truly absent
        if risk == "inactivity" and (hour < 9 or hour > 21 or any_motion):
            continue
        # Stove alerts only if stove was actually ON in this window
        if risk in ("stove_on", "stove_unattended") and not stove_on_in_window:
            continue
        # Water heater only if it is still on at end of window
        if risk == "water_heater_on" and not heater_currently_on:
            continue
        # Medication: rule engine fires deterministically at 10:00 and 21:00 — block LLM entirely
        if risk == "medication_missed":
            continue
        # Night exit: only during actual night hours AND only if door was actually opened
        if risk == "night_exit" and (6 <= hour <= 22 or not door_opened_in_window):
            continue
        # Fridge only if door is genuinely open (no close event after last open)
        if risk == "fridge_left_open" and not fridge_open_unclosed:
            continue
        # no_toilet_use: rule engine checks once at 21:00 — block LLM from ever generating it
        if risk == "no_toilet_use":
            continue
        # Handwash: only if toilet was actually cleared (vacated) in THIS window AND soap not seen today
        if risk == "no_handwash_after_toilet" and (not toilet_cleared_in_window or soap_used_day):
            continue

        result.append(a)
    return result


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
    from sensor_model_loader import ACTIVITY_SENSOR_IDS
    any_motion = any(e["sensor_id"] in ACTIVITY_SENSOR_IDS for e in long_window)

    # Full-day window for daily checks
    base_date = anchor_ts[:10]
    day_window = get_window(f"{base_date}T{anchor_ts[11:13]}:00:00", hours=int(anchor_ts[11:13]) - 7 + 1)
    day_sensor_ids = {e["sensor_id"] for e in day_window}

    alerts = []
    hour = datetime.fromisoformat(anchor_ts).hour

    # --- RULE 1: Stove left on ---
    if state.get("STOVE_POWER_01") == "1":
        alerts.append(_make_alert(anchor_ts, "stove_on",
            "high",
            f"Stove is still ON at {anchor_ts[11:16]}. No off event detected in the last hour."))

    # --- RULE 2: Stove on + door opened (left home while cooking) ---
    # Check for an open EVENT in the window — not the final state (door closes behind them)
    door_opened_in_window = any(
        e["sensor_id"] == "DOOR_CONTACT_01" and e["value"] == "1"
        for e in window_events
    )
    if state.get("STOVE_POWER_01") == "1" and door_opened_in_window:
        alerts.append(_make_alert(anchor_ts, "stove_unattended",
            "critical",
            "Stove is ON and front door was opened. Resident may have left home while cooking."))

    # --- RULE 3: Medication not taken by 10:00 — alert ONCE at 10:00 and once at 21:00 ---
    if hour in (10, 21):
        day_events = get_window(anchor_ts, hours=hour - 6)
        med_taken_today = any(
            e["sensor_id"] == "MED_BOX_01" and e["value"] == "1"
            for e in day_events
        )
        if not med_taken_today:
            severity = "critical" if hour == 21 else "medium"
            alerts.append(_make_alert(anchor_ts, "medication_missed",
                severity,
                f"Medication box has not been used today by {anchor_ts[11:16]}."))

    # --- RULE 4: No motion detected for 3+ hours during daytime ---
    if 9 <= hour <= 21 and not any_motion:
        alerts.append(_make_alert(anchor_ts, "inactivity",
            "medium",
            f"No movement detected in {INACTIVITY_THRESHOLD_HOURS} hours ending at {anchor_ts[11:16]}."))

    # --- RULE 5: Night exit (door opened between 23:00–05:00) ---
    # Check for an open EVENT — door closes behind the resident, so final state is "0"
    night_door_opened = any(
        e["sensor_id"] == "DOOR_CONTACT_01" and e["value"] == "1"
        for e in window_events
    )
    if (hour >= 23 or hour <= 5) and night_door_opened:
        alerts.append(_make_alert(anchor_ts, "night_exit",
            "high",
            f"Front door opened at {anchor_ts[11:16]}. Unusual night-time exit detected."))

    # --- RULE 6: Water heater left on without shower activity for 2+ hours ---
    heater_window = get_window(anchor_ts, hours=2)
    heater_states = get_latest_sensor_states(heater_window)
    heater_on = heater_states.get("WATER_HEATER_01") == "1"
    shower_in_window = any(
        e["sensor_id"] == "WATER_HEATER_01" and e["value"] == "0"
        for e in heater_window
    )
    if heater_on and not shower_in_window:
        alerts.append(_make_alert(anchor_ts, "water_heater_on",
            "medium",
            f"Water heater has been on for 2+ hours ending at {anchor_ts[11:16]} with no off event. Possible forgotten appliance."))

    # --- RULE 7: Fridge left open > 10 minutes ---
    fridge_events = [e for e in window_events if e["sensor_id"] == "FRIDGE_DOOR_01"]
    if fridge_events:
        fridge_opens  = [e for e in fridge_events if e["value"] == "1"]
        fridge_closes = [e for e in fridge_events if e["value"] == "0"]
        if fridge_opens:
            last_open_dt = datetime.fromisoformat(fridge_opens[-1]["simulated_ts"])
            last_close_dt = (
                datetime.fromisoformat(fridge_closes[-1]["simulated_ts"])
                if fridge_closes else None
            )
            # Only alert if last open has no subsequent close, AND it was > 10 min ago
            anchor_dt = datetime.fromisoformat(anchor_ts)
            if last_close_dt is None or last_close_dt < last_open_dt:
                minutes_open = (anchor_dt - last_open_dt).total_seconds() / 60
                if minutes_open > 10:
                    alerts.append(_make_alert(anchor_ts, "fridge_left_open",
                        "low",
                        f"Fridge door opened at {fridge_opens[-1]['simulated_ts'][11:16]} "
                        f"and not closed for {int(minutes_open)} minutes."))

    # --- RULE 8: Post-toilet hand wash check ---
    # If toilet was used in the window, verify soap was used and water flowed afterwards
    toilet_used = any(
        e["sensor_id"] == "TOILET_OCCUPANCY_01" and e["value"] == "0"
        for e in window_events
    )
    if toilet_used:
        soap_after_toilet = any(e["sensor_id"] == "SOAP_VIB_01" and e["value"] == "1" for e in window_events)
        water_after_toilet = any(e["sensor_id"] == "BATH_WATER_01" and e["value"] == "1" for e in window_events)
        if not (soap_after_toilet and water_after_toilet):
            alerts.append(_make_alert(anchor_ts, "no_handwash_after_toilet",
                "medium",
                f"Toilet was used at {anchor_ts[11:16]} but no hand washing detected afterwards."))

    # --- RULE 9: No toilet use detected all day (check once at 21:00) ---
    if hour == 21:
        toilet_today = any(
            e["sensor_id"] == "TOILET_OCCUPANCY_01" and e["value"] == "1"
            for e in get_window(anchor_ts, hours=14)  # 07:00 to 21:00
        )
        if not toilet_today:
            alerts.append(_make_alert(anchor_ts, "no_toilet_use",
                "high",
                "No toilet use detected today (07:00–21:00). Possible health or mobility concern."))

    # --- LLM layer: Care Plan audit via Ollama (merges with rule-based alerts) ---
    llm_alerts = _llm_audit(anchor_ts, window_events)
    llm_alerts = _post_filter_llm_alerts(llm_alerts, anchor_ts, window_events)
    existing_risks = {a["risk"] for a in alerts}
    for la in llm_alerts:
        if la["risk"] not in existing_risks:   # avoid duplicating what Python rules already caught
            alerts.append(la)
            existing_risks.add(la["risk"])

    # Persist alerts
    if alerts:
        existing = _load_alerts()
        existing.extend(alerts)
        _save_alerts(existing)

    return alerts


def run_full_day_audit(base_date: str) -> list:
    """
    Run audits at every hour checkpoint from 07:00 to 23:00 (same day)
    and 00:00 to 05:00 of the next day (to catch night-time exits).
    base_date: YYYY-MM-DD string
    """
    from datetime import datetime as _dt, timedelta as _td
    all_alerts = []

    # Clear previous alerts for this run
    _save_alerts([])

    # Same-day audit: 07:00 – 23:00
    for hour in range(7, 24):
        anchor_ts = f"{base_date}T{hour:02d}:00:00"
        alerts = run_audit(anchor_ts)
        if alerts:
            for a in alerts:
                print(f"  [{a['severity'].upper()}] {a['risk']} @ {anchor_ts[11:16]}: {a['reason']}")
        all_alerts.extend(alerts)

    # Next-day early morning: 00:00 – 05:00 (catches 3 AM night exits)
    next_date = (_dt.strptime(base_date, "%Y-%m-%d") + _td(days=1)).strftime("%Y-%m-%d")
    for hour in range(0, 6):
        anchor_ts = f"{next_date}T{hour:02d}:00:00"
        alerts = run_audit(anchor_ts)
        if alerts:
            for a in alerts:
                print(f"  [{a['severity'].upper()}] {a['risk']} @ {anchor_ts[11:16]} (next day): {a['reason']}")
        all_alerts.extend(alerts)

    return all_alerts
