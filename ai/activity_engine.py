import json
import os

# Load rule mapping from config/
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_root, "config", "rules.json"), "r") as f:
    RULE_MAP = json.load(f)

# Sensor definitions — single source of truth from sensor_model.json
from sensor_model_loader import SENSOR_IDS as KNOWN_SENSORS


def build_sensor_map(events):
    """Returns a dict of sensor_id → latest value."""
    sensor_map = {s: None for s in KNOWN_SENSORS}
    for e in events:
        sid = e.get("sensor_id")
        if sid in sensor_map:
            sensor_map[sid] = e.get("value")
    return sensor_map


def detect_activities(events):
    """
    events = list of telemetry dicts from ThingsBoard
    Each event: {sensor_id, value}
    """
    sensor_map = build_sensor_map(events)
    activities = set()

    # WAKE UP
    if sensor_map["BED_PRESSURE_01"] == "empty" and sensor_map["BEDROOM_PIR_01"]:
        activities.add(RULE_MAP["wake_up"])

    # HYGIENE
    if sensor_map["BATH_WATER_01"] == "flow" and sensor_map["SOAP_VIB_01"] == "used":
        activities.add(RULE_MAP["hygiene"])

    # EATING
    if sensor_map["FRIDGE_DOOR_01"] == "open" and sensor_map["KITCHEN_PIR_01"]:
        activities.add(RULE_MAP["eating"])

    # MEDICATION
    if sensor_map["MED_BOX_01"] == "used":
        activities.add(RULE_MAP["medication"])

    # COOKING / RISK
    if sensor_map["STOVE_POWER_01"] == "on":
        activities.add(RULE_MAP["cooking_risk"])

    # LEAVING HOME
    if sensor_map["DOOR_CONTACT_01"] == "open":
        activities.add(RULE_MAP["leaving_home"])

    return list(activities)