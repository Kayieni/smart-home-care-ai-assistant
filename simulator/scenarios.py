import time
from simulator.mqtt_client import send


def reset_all_sensors():
    """Push neutral/off state for every sensor before running a scenario."""
    send("BED_PRESSURE_01",  "pressure",    "bedroom",       "occupied")
    send("BEDROOM_PIR_01",   "pir",         "bedroom",       "no_motion")
    send("BATH_WATER_01",    "water_flow",  "bathroom_sink", "no_flow")
    send("SOAP_VIB_01",      "vibration",   "soap",          "not_used")
    send("FRIDGE_DOOR_01",   "contact",     "kitchen",       "closed")
    send("KITCHEN_PIR_01",   "pir",         "kitchen",       "no_motion")
    send("MED_BOX_01",       "vibration",   "medicine",      "not_used")
    send("STOVE_POWER_01",   "smart_plug",  "kitchen",       "off")
    send("DOOR_CONTACT_01",  "contact",     "entrance",      "closed")
    send("HALLWAY_PIR_01",   "pir",         "hallway",       "no_motion")
    print("--- Sensors reset to neutral ---")
    time.sleep(1)


# ---------------- NORMAL ----------------
def run_normal():
    reset_all_sensors()

    send("BED_PRESSURE_01", "pressure",   "bedroom",       "empty")
    time.sleep(2)

    send("BATH_WATER_01",   "water_flow", "bathroom_sink", "flow")
    time.sleep(2)

    send("SOAP_VIB_01",     "vibration",  "soap",          "used")
    time.sleep(2)

    send("FRIDGE_DOOR_01",  "contact",    "kitchen",       "open")
    time.sleep(2)

    send("MED_BOX_01",      "vibration",  "medicine",      "used")


# ---------------- DECLINE ----------------
def run_decline():
    reset_all_sensors()

    send("BED_PRESSURE_01", "pressure",  "bedroom", "empty")
    send("FRIDGE_DOOR_01",  "contact",   "kitchen", "open")

    # medication explicitly not taken
    send("MED_BOX_01",      "vibration", "medicine", "not_used")

    time.sleep(5)


# ---------------- HAZARD ----------------
def run_hazard():
    reset_all_sensors()

    send("STOVE_POWER_01",  "smart_plug", "kitchen",  "on")
    send("DOOR_CONTACT_01", "contact",    "entrance", "open")

    time.sleep(3)

    # stove still on — resident has left
    send("STOVE_POWER_01",  "smart_plug", "kitchen",  "on")
