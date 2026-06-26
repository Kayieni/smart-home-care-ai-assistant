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
from ai.app_settings import TIME_SCALE

# ---------------------------------------------------------------------------
# SCENARIO TIMELINES
# Each entry: (hour, minute, sensor_id, sensor_type, location, value)
# ---------------------------------------------------------------------------

TIMELINE_NORMAL = [
    # --- Morning routine ---
    (7,  0,  "BED_PRESSURE_01",  "pressure",     "bedroom",        0),
    (7,  5,  "BEDROOM_PIR_01",   "pir",           "bedroom",        1),
    # Toilet visit + hand wash
    (7, 10,  "TOILET_OCCUPANCY_01", "occupancy", "bathroom_toilet", 1),
    (7, 15,  "TOILET_OCCUPANCY_01", "occupancy", "bathroom_toilet", 0),
    (7, 16,  "BATH_WATER_01",    "water_flow",    "bathroom_sink",  1),
    (7, 18,  "SOAP_VIB_01",      "vibration",     "soap",           1),
    (7, 22,  "BATH_WATER_01",    "water_flow",    "bathroom_sink",  0),
    # Water heater on for shower, then off
    (7, 23,  "WATER_HEATER_01",  "smart_plug",    "bathroom_heater",1),
    (7, 55,  "WATER_HEATER_01",  "smart_plug",    "bathroom_heater",0),
    # Breakfast
    (8,  0,  "FRIDGE_DOOR_01",   "contact",       "kitchen",        1),
    (8,  5,  "KITCHEN_PIR_01",   "pir",           "kitchen",        1),
    (8,  8,  "FRIDGE_DOOR_01",   "contact",       "kitchen",        0),
    # Hand wash after breakfast prep
    (8, 10,  "BATH_WATER_01",    "water_flow",    "bathroom_sink",  1),
    (8, 12,  "SOAP_VIB_01",      "vibration",     "soap",           1),
    (8, 14,  "BATH_WATER_01",    "water_flow",    "bathroom_sink",  0),
    # Medication
    (9,  0,  "MED_BOX_01",       "vibration",     "medicine",       1),
    # Lunch
    (12, 0,  "FRIDGE_DOOR_01",   "contact",       "kitchen",        1),
    (12, 5,  "KITCHEN_PIR_01",   "pir",           "kitchen",        1),
    (12, 8,  "FRIDGE_DOOR_01",   "contact",       "kitchen",        0),
    # Balcony â€” water plants
    (14, 0,  "BALCONY_PIR_01",   "pir",           "balcony",        1),
    (14, 30, "SOIL_MOISTURE_01", "soil_moisture", "balcony_plants", "65"),
    (14, 35, "BALCONY_PIR_01",   "pir",           "balcony",        0),
    # Hallway movement
    (14, 40, "HALLWAY_PIR_01",   "pir",           "hallway",        1),
    # Dinner â€” cooking on stove
    (16, 0,  "KITCHEN_PIR_01",   "pir",           "kitchen",        1),
    (18, 0,  "FRIDGE_DOOR_01",   "contact",       "kitchen",        1),
    (18, 3,  "FRIDGE_DOOR_01",   "contact",       "kitchen",        0),
    (18, 5,  "STOVE_POWER_01",   "smart_plug",    "kitchen",        1),
    (18, 35, "STOVE_POWER_01",   "smart_plug",    "kitchen",        0),
    # Hand wash after cooking
    (18, 37, "BATH_WATER_01",    "water_flow",    "bathroom_sink",  1),
    (18, 39, "SOAP_VIB_01",      "vibration",     "soap",           1),
    (18, 41, "BATH_WATER_01",    "water_flow",    "bathroom_sink",  0),
    # Evening medication before bed
    (21, 30, "MED_BOX_01",       "vibration",     "medicine",       1),
    # Bedtime
    (22, 0,  "BED_PRESSURE_01",  "pressure",      "bedroom",        1),
]

TIMELINE_DECLINE = [
    # Late wake-up
    (8,  0,  "BED_PRESSURE_01",  "pressure",      "bedroom",        0),
    (8,  5,  "BEDROOM_PIR_01",   "pir",            "bedroom",        1),
    # Skipped hygiene â€” no soap used, no toilet flush
    (8, 30,  "BATH_WATER_01",    "water_flow",     "bathroom_sink",  0),
    (8, 30,  "SOAP_VIB_01",      "vibration",      "soap",           0),
    # Breakfast â€” fridge left open for 15 minutes (forgetfulness)
    (9,  0,  "FRIDGE_DOOR_01",   "contact",        "kitchen",        1),
    (9,  5,  "KITCHEN_PIR_01",   "pir",            "kitchen",        1),
    (9, 15,  "FRIDGE_DOOR_01",   "contact",        "kitchen",        0),  # left open 15min
    # Morning medication not taken (forgetfulness)
    (9, 30,  "MED_BOX_01",       "vibration",      "medicine",       0),
    # --- 6-hour inactivity gap: 09:30 to 15:30 — no PIR events ---
    # Only one more meal, very late
    (15, 30, "FRIDGE_DOOR_01",   "contact",        "kitchen",        1),
    (15, 35, "KITCHEN_PIR_01",   "pir",            "kitchen",        1),
    (15, 38, "FRIDGE_DOOR_01",   "contact",        "kitchen",        0),
    # No cooking, no balcony, no social activity
    # Evening medication also not taken
    (21,  0, "MED_BOX_01",       "vibration",      "medicine",       0),
    (23, 0,  "BED_PRESSURE_01",  "pressure",       "bedroom",        1),
]

TIMELINE_HAZARD = [
    # Normal morning routine
    (7,  0,  "BED_PRESSURE_01",     "pressure",    "bedroom",          0),
    (7,  5,  "BEDROOM_PIR_01",      "pir",          "bedroom",          1),
    (7, 10,  "TOILET_OCCUPANCY_01", "occupancy",   "bathroom_toilet",   1),
    (7, 15,  "TOILET_OCCUPANCY_01", "occupancy",   "bathroom_toilet",   0),
    (7, 16,  "BATH_WATER_01",       "water_flow",  "bathroom_sink",     1),
    (7, 18,  "SOAP_VIB_01",         "vibration",   "soap",              1),
    (7, 22,  "BATH_WATER_01",       "water_flow",  "bathroom_sink",     0),
    # Water heater turned on -- and FORGOTTEN (never turned off)
    (7, 23,  "WATER_HEATER_01",     "smart_plug",  "bathroom_heater",   1),
    # Breakfast
    (8,  0,  "FRIDGE_DOOR_01",      "contact",     "kitchen",           1),
    (8,  5,  "KITCHEN_PIR_01",      "pir",          "kitchen",           1),
    (8,  8,  "FRIDGE_DOOR_01",      "contact",     "kitchen",           0),
    # Morning medication taken after breakfast
    (8, 30,  "MED_BOX_01",          "vibration",   "medicine",          1),
    # Lunch -- stove turned on, resident leaves while cooking (the core hazard)
    (12,  0, "FRIDGE_DOOR_01",      "contact",     "kitchen",           1),
    (12,  5, "KITCHEN_PIR_01",      "pir",          "kitchen",           1),
    (12,  8, "FRIDGE_DOOR_01",      "contact",     "kitchen",           0),
    (12, 10, "STOVE_POWER_01",      "smart_plug",  "kitchen",           1),
    (12, 12, "OVEN_TEMP_01",        "temperature", "kitchen_oven",      "80"),   # just started -- low temp
    (12, 15, "DOOR_CONTACT_01",     "contact",     "entrance",          1),  # leaves while cooking!
    (12, 16, "HALLWAY_PIR_01",      "pir",          "hallway",           1),
    (12, 17, "DOOR_CONTACT_01",     "contact",     "entrance",          0),  # door closes behind them
    # Stove still on -- oven temperature climbs dangerously while nobody is home
    (13, 30, "OVEN_TEMP_01",        "temperature", "kitchen_oven",      "210"),  # nobody home -- critical temp
    # Resident returns ~3 hours later (stove_unattended alert fires at 13:00 + 14:00 audits)
    (15, 30, "DOOR_CONTACT_01",     "contact",     "entrance",          1),  # returns home
    (15, 31, "DOOR_CONTACT_01",     "contact",     "entrance",          0),  # door closes
    (15, 32, "HALLWAY_PIR_01",      "pir",          "hallway",           1),
    (15, 35, "STOVE_POWER_01",      "smart_plug",  "kitchen",           0),  # turns stove off upon return
    # Evening medication before bed
    (21,  0, "MED_BOX_01",          "vibration",   "medicine",          1),
    # Bedtime
    (22,  0, "BED_PRESSURE_01",     "pressure",    "bedroom",           1),
    # Night-time exit -- resident gets up and leaves at ~02:59 NEXT DAY (acute hazard)
    # Use hour 26 min 55 = tomorrow 02:55, hour 26 min 59 = tomorrow 02:59
    # Door open at 02:59 lands cleanly in the 03:00 audit window (02:00-03:00),
    # NOT in the 04:00 window, so the alert fires exactly once at 03:00.
    (26, 55, "BED_PRESSURE_01",     "pressure",    "bedroom",           0),  # gets out of bed at 02:55
    (26, 57, "BEDROOM_PIR_01",      "pir",          "bedroom",           1),  # motion in bedroom
    (26, 59, "DOOR_CONTACT_01",     "contact",     "entrance",          1),  # opens front door at 02:59
    (27,  0, "HALLWAY_PIR_01",      "pir",          "hallway",           1),  # hallway motion at 03:00
    (27,  1, "DOOR_CONTACT_01",     "contact",     "entrance",          0),  # door closes -- resident outside at 03:01
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

    # Determine which dates this simulation covers (hour > 23 spills into next day)
    max_hour = sorted_events[-1][0]
    sim_dates = [base_date.strftime("%Y-%m-%d")]
    if max_hour >= 24:
        sim_dates.append((base_date + timedelta(days=1)).strftime("%Y-%m-%d"))

    init_db()
    clear_events(sim_dates)

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



