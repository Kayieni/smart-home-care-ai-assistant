import requests
from app_settings import OLLAMA_URL, OLLAMA_MODEL, LLM_TIMEOUT

ACTIVITY_LABELS = {
    "wake_up": "woke up and got out of bed",
    "hygiene": "completed their hygiene routine (soap and water detected)",
    "eating": "opened the fridge (meal preparation likely)",
    "medication_taken": "took their medication",
    "cooking_risk": "used the stove",
    "leaving_home": "opened the front door (possible departure)",
    "toilet_use": "used the toilet",
    "water_heater_used": "used the water heater (shower likely)",
    "balcony_visit": "visited the balcony",
    "plant_watering": "watered the plants on the balcony",
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def generate_report(activities: list, risks: list) -> str:
    """
    Generates a natural language caregiver summary.
    Uses Ollama (local LLM) if available, otherwise falls back to templates.
    """
    try:
        return _ollama_report(activities, risks)
    except Exception:
        return _template_report(activities, risks)


def _ollama_report(activities: list, risks: list) -> str:
    activity_text = ", ".join(activities) if activities else "none detected"

    # Sort risks so critical/high appear first
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_risks = sorted(risks, key=lambda r: severity_order.get(r.get("severity", "low"), 9))
    risk_lines = "\n".join(
        f"- [{r['severity'].upper()}] {r['risk']}: {r['reason']}"
        for r in sorted_risks
    ) if sorted_risks else "- none"

    critical_and_high = [r for r in sorted_risks if r.get("severity") in ("critical", "high")]
    urgent_note = (
        "URGENT — the following CRITICAL or HIGH risks MUST be mentioned explicitly and prominently:\n"
        + "\n".join(f"  * [{r['severity'].upper()}] {r['risk']}: {r['reason']}" for r in critical_and_high)
    ) if critical_and_high else "No critical or high risks today."

    prompt = f"""You are a Compassionate Context Engine for an elderly care monitoring system.
Translate sensor observations into a warm, clear caregiver report for a family member or care professional.

RULES — follow these exactly:
1. Write 3–5 plain-language sentences. No bullet points.
2. {urgent_note}
3. Each CRITICAL or HIGH risk must appear as its own sentence and be described clearly.
4. Do NOT add any notes, disclaimers, meta-commentary, or text in parentheses after the report.
5. Do not list raw sensor IDs. Describe events in human terms.
6. Keep a compassionate, professional tone throughout.

ACTIVITIES OBSERVED TODAY: {activity_text}

ALL SAFETY RISKS (sorted by severity):
{risk_lines}

Write the caregiver report now:"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=LLM_TIMEOUT
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def _template_report(activities: list, risks: list) -> str:
    lines = []

    if activities:
        readable = [ACTIVITY_LABELS.get(a, a) for a in activities]
        lines.append(
            "Today the resident " + ", ".join(readable[:-1])
            + (" and " if len(readable) > 1 else "")
            + readable[-1] + "."
        )
    else:
        lines.append("No resident activity was detected today.")

    if risks:
        sorted_risks = sorted(risks, key=lambda r: SEVERITY_ORDER.get(r["severity"], 9))
        for r in sorted_risks:
            severity = r["severity"].upper()
            lines.append(f"[{severity} ALERT] {r['reason']}")
        lines.append("Immediate caregiver follow-up is recommended.")
    else:
        lines.append("No safety concerns were detected. The resident appears to be managing well.")

    return "\n".join(lines)


def answer_question(question: str, summary: dict) -> str:
    """
    Answers a caregiver's natural-language question about the resident's day.
    Uses Ollama if available, otherwise falls back to a keyword-based response.
    """
    try:
        return _ollama_answer(question, summary)
    except Exception:
        return _template_answer(question, summary)


def _ollama_answer(question: str, summary: dict) -> str:
    activities = summary.get("activities_detected", [])
    alerts = summary.get("alerts", [])
    timeline = summary.get("timeline", [])

    # Decode activities to plain English using the label map
    activity_text = (
        ", ".join(ACTIVITY_LABELS.get(a, a) for a in activities)
        if activities else "none detected"
    )

    risk_lines = "\n".join(
        f"- [{r['severity'].upper()}] {r['risk']}: {r['reason']}"
        for r in alerts
    ) if alerts else "- none"

    # Decode raw sensor values to human-readable labels for the timeline
    from sensor_model_loader import decode_value
    timeline_text = "\n".join(
        f"  {e['time']} — {e['sensor']}: {decode_value(e['sensor'], e['value'])}"
        for e in timeline[:40]
    ) if timeline else "  (no events)"

    prompt = f"""You are a Compassionate Context Engine for an elderly care monitoring system.
Answer questions from family members and care professionals about the resident's day.

IMPORTANT — sensor interpretation rules (treat these as confirmed facts, not guesses):
- BED_PRESSURE_01 = empty → resident got out of bed (woke up)
- BED_PRESSURE_01 = occupied → resident went to bed
- MED_BOX_01 = used → resident took their medication
- SOAP_VIB_01 = used + BATH_WATER_01 = flow → resident washed their hands
- TOILET_OCCUPANCY_01 = occupied → resident used the toilet
- WATER_HEATER_01 = on → resident took a shower
- FRIDGE_DOOR_01 = open → resident had a meal or snack
- STOVE_POWER_01 = on → resident was cooking
- DOOR_CONTACT_01 = open → resident opened the front door (left or arrived home)
- BALCONY_PIR_01 = motion → resident was on the balcony
- SOIL_MOISTURE_01 reading → resident watered the plants
- PIR sensors = motion → resident was present in that room

When a sensor event is in the data, state its meaning as fact. Do not hedge with
phrases like "may indicate", "suggests", or "cannot confirm" — the sensor data IS
the evidence. Only say something is unknown if no relevant sensor fired at all.

Today's summary for {summary.get('date', 'today')}:

ACTIVITIES CONFIRMED: {activity_text}

SAFETY ALERTS:
{risk_lines}

EVENT TIMELINE:
{timeline_text}

Caregiver question: "{question}"

Answer in 1-3 warm, clear sentences using only the data above.
If no relevant sensor data exists, say so plainly.
"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=LLM_TIMEOUT
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def _template_answer(question: str, summary: dict) -> str:
    """Keyword-based fallback when Ollama is unavailable."""
    q = question.lower()
    activities = summary.get("activities_detected", [])
    alerts = summary.get("alerts", [])
    alert_counts = summary.get("alert_counts", {})

    if any(w in q for w in ["medic", "pill", "tablet"]):
        if "medication_taken" in activities:
            return "Yes, the resident took their medication today."
        return "No medication event was detected today. Please follow up."

    if any(w in q for w in ["eat", "food", "fridge", "meal"]):
        if "eating" in activities:
            return "The resident opened the fridge today, suggesting they had a meal."
        return "No eating activity was detected today."

    if any(w in q for w in ["bath", "shower", "hygiene", "wash"]):
        if "hygiene" in activities:
            return "The resident completed their hygiene routine today."
        return "No hygiene activity was recorded today."

    if any(w in q for w in ["alert", "risk", "danger", "concern", "safe"]):
        total = alert_counts.get("total", 0)
        critical = alert_counts.get("critical", 0)
        if total == 0:
            return "No safety alerts were raised today. The resident appears to be safe."
        return (
            f"There were {total} alert(s) today"
            + (f", including {critical} critical" if critical else "")
            + ". " + "; ".join(a["reason"] for a in alerts[:3])
        )

    if any(w in q for w in ["leav", "outside", "door", "out"]):
        if "leaving_home" in activities:
            return "The front door was opened today, suggesting the resident may have gone outside."
        return "No departure from home was detected today."

    if any(w in q for w in ["stove", "cook", "oven", "fire"]):
        if "cooking_risk" in activities:
            return "The stove was used today. Please check for any related safety alerts."
        return "No stove usage was detected today."

    if any(w in q for w in ["wake", "bed", "sleep", "morning"]):
        if "wake_up" in activities:
            return "The resident woke up and got out of bed today."
        return "No wake-up event was detected today."

    return "I don't have enough sensor data to answer that question precisely. Please check the full timeline."

