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
    risk_lines = "\n".join(
        f"- [{r['severity'].upper()}] {r['risk']}: {r['reason']}"
        for r in risks
    ) if risks else "- none"

    from sensor_model_loader import sensor_context_for_prompt
    sensor_context = sensor_context_for_prompt()

    prompt = f"""You are a Compassionate Context Engine for an elderly care monitoring system.
Your role is to translate raw sensor data into warm, empathetic, natural language summaries
for family members and care professionals. Do not list raw sensor IDs or timestamps unless
specifically asked. Focus on human-scale activities: waking up, hygiene, eating, medication,
cooking, social or leisure activities, and safety. If high-severity risks exist, highlight
them clearly but compassionately — the reader may be a worried family member.

SENSOR CATALOGUE (for reference):
{sensor_context}

ACTIVITIES OBSERVED: {activity_text}

SAFETY RISKS:
{risk_lines}

Write a concise, empathetic caregiver report (3–5 sentences) summarising the resident's day
and any concerns. Use plain language suitable for a family member or care professional.
If there are high-severity or critical risks, make sure those are clearly highlighted.
"""

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

    activity_text = ", ".join(activities) if activities else "none detected"
    risk_lines = "\n".join(
        f"- [{r['severity'].upper()}] {r['risk']}: {r['reason']}"
        for r in alerts
    ) if alerts else "- none"
    timeline_text = "\n".join(
        f"  {e['time']} — {e['sensor']}: {e['value']}"
        for e in timeline[:30]  # limit to avoid token overflow
    ) if timeline else "  (no events)"

    prompt = f"""You are a Compassionate Context Engine for an elderly care monitoring system.
Your role is to answer questions from family members and care professionals about the
resident's day, based strictly on sensor data. Be warm, clear and honest. If the sensors
did not capture something, say so — do not speculate beyond what the data shows.

Today's summary for {summary.get('date', 'today')}:

ACTIVITIES OBSERVED: {activity_text}

SAFETY RISKS:
{risk_lines}

EVENT TIMELINE:
{timeline_text}

A caregiver asks: \"{question}\"

Answer clearly and concisely in 1-3 sentences, based only on the data above.
If the data does not contain enough information, say so honestly.
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

