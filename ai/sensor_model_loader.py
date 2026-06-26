"""
Sensor Model Loader
-------------------
Single source of truth for all sensor definitions.
Reads config/sensor_model.json and exposes typed accessors used
throughout the AI pipeline and simulator.
"""

import json
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODEL_PATH = os.path.join(_root, "config", "sensor_model.json")

with open(_MODEL_PATH, "r") as _f:
    _raw = json.load(_f)

# List of all sensor dicts as defined in sensor_model.json
SENSORS: list[dict] = _raw["sensors"]

# Flat list of all sensor IDs
SENSOR_IDS: list[str] = [s["sensor_id"] for s in SENSORS]

# sensor_id → full sensor dict (for O(1) lookup)
SENSOR_MAP: dict[str, dict] = {s["sensor_id"]: s for s in SENSORS}

# Sensors that indicate resident presence/activity (used for inactivity detection)
# Excludes purely state sensors like OVEN_TEMP_01 and SOIL_MOISTURE_01
ACTIVITY_SENSOR_IDS: set[str] = {
    s["sensor_id"] for s in SENSORS
    if s["type"] not in ("temperature", "soil_moisture")
}


def get_sensor(sensor_id: str) -> dict | None:
    """Return the full sensor definition for a given sensor_id, or None."""
    return SENSOR_MAP.get(sensor_id)


def sensors_by_risk_category(category: str) -> list[dict]:
    """Return all sensors belonging to a given risk_category."""
    return [s for s in SENSORS if s.get("risk_category") == category]


def sensors_by_activity(activity: str) -> list[dict]:
    """Return all sensors associated with a given activity."""
    return [s for s in SENSORS if s.get("activity") == activity]


def _format_values(s: dict) -> str:
    """Return a human-readable value description from the new schema."""
    if s.get("value_format") == "boolean":
        vm = s.get("value_map", {})
        return f"boolean — 1={vm.get('1','on')}, 0={vm.get('0','off')}"
    elif s.get("value_format") == "integer":
        return f"integer ({s.get('unit', 'numeric')})"
    # fallback for any legacy entries
    return ", ".join(s.get("possible_values", []))


def decode_value(sensor_id: str, raw) -> str:
    """
    Convert a raw 0/1 or numeric value to its human-readable label.
    E.g. decode_value("BED_PRESSURE_01", 1) → "occupied"
         decode_value("OVEN_TEMP_01", 210) → "210 °C"
    """
    s = SENSOR_MAP.get(sensor_id)
    if not s:
        return str(raw)
    if s.get("value_format") == "boolean":
        return s.get("value_map", {}).get(str(int(raw)), str(raw))
    elif s.get("value_format") == "integer":
        return f"{raw} {s.get('unit', '')}"
    # legacy string values pass through unchanged
    return str(raw)


def sensor_context_for_prompt() -> str:
    """
    Returns a compact natural-language description of all sensors
    suitable for injection into an LLM prompt.
    """
    lines = []
    for s in SENSORS:
        lines.append(
            f"  - {s['sensor_id']} ({s['type']}) @ {s['location']}: "
            f"monitors {s['activity']} [{s['risk_category']}] — {_format_values(s)}"
        )
    return "\n".join(lines)
