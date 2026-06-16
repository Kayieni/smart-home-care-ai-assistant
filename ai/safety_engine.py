def detect_risks(sensor_map, activities):
    """
    Evaluates sensor state and detected activities for safety hazards.

    Returns a list of risk dicts:
        { "risk": str, "severity": "low" | "medium" | "high", "reason": str }
    """
    risks = []

    # --- HAZARD 1: Stove left on while resident has left home ---
    if (sensor_map.get("STOVE_POWER_01") == "on" and
            sensor_map.get("DOOR_CONTACT_01") == "open"):
        risks.append({
            "risk": "stove_unattended",
            "severity": "high",
            "reason": "Stove is on and front door was opened — resident may have left while cooking."
        })

    # --- HAZARD 2: Medication not taken ---
    if sensor_map.get("MED_BOX_01") == "not_used":
        risks.append({
            "risk": "medication_missed",
            "severity": "medium",
            "reason": "Medicine box was not interacted with during the expected window."
        })

    # --- HAZARD 3: No activity detected at all (inactivity risk) ---
    if len(activities) == 0:
        risks.append({
            "risk": "no_activity_detected",
            "severity": "low",
            "reason": "No sensor activity detected. Resident may be inactive or sensors are offline."
        })

    return risks
