"""
Time Simulation Engine
----------------------
Defines full-day event timelines as (hour, minute, sensor_id, type, location, value).
The engine compresses simulated time: each simulated hour = TIME_SCALE real seconds.
All events are published to MQTT with their simulated timestamp in the payload.
"""

import time
import json
from datetime import datetime, timedelta
from simulator.mqtt_client import client
from ai.storage import init_db, store_event, clear_events

# 1 simulated hour = this many real seconds (3 = full day in ~48s)
TIME_SCALE = 3

# ---------------------------------------------------------------------------
# SCENARIO TIMELINES
# Each entry: (hour, minute, sensor_id, sensor_type, location, value)
# ---------------------------------------------------------------------------

TIMELINE_NORMAL = [
    (7,  0,  "BED_PRESSURE_01",  "pressure",    "bedroom",       "empty"),
    (7,  5,  "BEDROOM_PIR_01",   "pir",          "bedroom",       "motion"),
    (7, 15,  "BATH_WATER_01",    "water_flow",   "bathroom_sink", "flow"),
    (7, 17,  "SOAP_VIB_01",      "vibration",    "soap",          "used"),
    (7, 30,  "BATH_WATER_01",    "water_flow",   "bathroom_sink", "no_flow"),
    (8,  0,  "FRIDGE_DOOR_01",   "contact",      "kitchen",       "open"),
    (8,  5,  "KITCHEN_PIR_01",   "pir",          "kitchen",       "motion"),
    (8, 10,  "FRIDGE_DOOR_01",   "contact",      "kitchen",       "closed"),
    (9,  0,  "MED_BOX_01",       "vibration",    "medicine",      "used"),
    (12, 0,  "FRIDGE_DOOR_01",   "contact",      "kitchen",       "open"),
    (12, 5,  "KITCHEN_PIR_01",   "pir",          "kitchen",       "motion"),
    (14, 30, "HALLWAY_PIR_01",   "pir",          "hallway",       "motion"),
    (16, 0,  "KITCHEN_PIR_01",   "pir",          "kitchen",       "motion"),
    (18, 0,  "FRIDGE_DOOR_01",   "contact",      "kitchen",       "open"),
    (18, 5,  "STOVE_POWER_01",   "smart_plug",   "kitchen",       "on"),
    (18, 35, "STOVE_POWER_01",   "smart_plug",   "kitchen",       "off"),
    (22, 0,  "BED_PRESSURE_01",  "pressure",     "bedroom",       "occupied"),
]

TIMELINE_DECLINE = [
    (8,  0,  "BED_PRESSURE_01",  "pressure",    "bedroom",       "empty"),   # late wake-up
    (8, 30,  "BATH_WATER_01",    "water_flow",   "bathroom_sink", "no_flow"), # skipped hygiene
    (8, 30,  "SOAP_VIB_01",      "vibration",    "soap",          "not_used"),
    (9,  0,  "FRIDGE_DOOR_01",   "contact",      "kitchen",       "open"),
    (9,  5,  "FRIDGE_DOOR_01",   "contact",      "kitchen",       "closed"),
    (9, 30,  "MED_BOX_01",       "vibration",    "medicine",      "not_used"), # missed medication
    (14, 0,  "FRIDGE_DOOR_01",   "contact",      "kitchen",       "open"),    # only one meal
    (23, 0,  "BED_PRESSURE_01",  "pressure",     "bedroom",       "occupied"),
]

TIMELINE_HAZARD = [
    (7,  0,  "BED_PRESSURE_01",  "pressure",    "bedroom",       "empty"),
    (7, 15,  "BATH_WATER_01",    "water_flow",   "bathroom_sink", "flow"),
    (7, 17,  "SOAP_VIB_01",      "vibration",    "soap",          "used"),
    (8,  0,  "FRIDGE_DOOR_01",   "contact",      "kitchen",       "open"),
    (8, 10,  "STOVE_POWER_01",   "smart_plug",   "kitchen",       "on"),
    (8, 15,  "DOOR_CONTACT_01",  "contact",      "entrance",      "open"),   # leaves while cooking
    (8, 16,  "HALLWAY_PIR_01",   "pir",          "hallway",       "motion"),
    # stove remains ON — no off event sent
    (9, 30,  "MED_BOX_01",       "vibration",    "medicine",      "not_used"),
]


def _publish_event(simulated_ts: datetime, sensor_id, sensor_type, location, value):
    """Publish a single timestamped event to ThingsBoard AND store it locally."""
    payload = {
        sensor_id: value,
        "_meta": {
            "sensor_id": sensor_id,
            "type": sensor_type,
            "location": location,
            "simulated_ts": simulated_ts.isoformat()
        }
    }
    client.publish("v1/devices/me/telemetry", json.dumps(payload))

    # persist to local storage
    store_event(simulated_ts.isoformat(), sensor_id, sensor_type, location, value)

    time.sleep(0.3)
    print(f"  [{simulated_ts.strftime('%H:%M')}] {sensor_id} = {value}")


def run_timeline(events: list, label: str = ""):
    """
    Run a timeline of events with compressed time simulation.
    Clears previous events, then publishes and stores each event in order.
    """
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    sorted_events = sorted(events, key=lambda e: (e[0], e[1]))

    init_db()
    clear_events()

    print(f"\n=== Running timeline: {label} ===")
    print(f"    {len(sorted_events)} events | 1 sim-hour = {TIME_SCALE}s real time\n")

    prev_sim_minutes = sorted_events[0][0] * 60 + sorted_events[0][1]

    for (hour, minute, sensor_id, sensor_type, location, value) in sorted_events:
        sim_minutes = hour * 60 + minute
        delta_minutes = sim_minutes - prev_sim_minutes
        real_sleep = (delta_minutes / 60) * TIME_SCALE
        if real_sleep > 0:
            time.sleep(real_sleep)
        prev_sim_minutes = sim_minutes

        simulated_ts = base_date + timedelta(hours=hour, minutes=minute)
        _publish_event(simulated_ts, sensor_id, sensor_type, location, value)

    print("\n=== Timeline complete ===\n")
