import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

ACTIVITY_LABELS = {
    "wake_up": "woke up",
    "hygiene": "completed their morning hygiene routine",
    "eating": "opened the fridge (possible meal preparation)",
    "medication_taken": "took their medication",
    "cooking_risk": "used the stove",
    "leaving_home": "opened the front door (possible departure)",
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

    prompt = f"""You are an AI caregiver assistant monitoring an elderly person living alone.

Based on today's smart home sensor data, here is what was detected:

ACTIVITIES OBSERVED:
{activity_text}

SAFETY RISKS DETECTED:
{risk_lines}

Write a concise, empathetic caregiver report (3-5 sentences) summarising the resident's day and any concerns.
Use plain language suitable for a family member or care professional.
If there are high-severity risks, make sure those are clearly highlighted.
"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=60
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

