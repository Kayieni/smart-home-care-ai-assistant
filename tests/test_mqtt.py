"""
test_mqtt.py
------------
Verifies that a single sensor event can be published to ThingsBoard via MQTT.
Run from project root: python tests/test_mqtt.py
"""

from simulator.mqtt_client import send

print("Testing MQTT publish...")
send("BED_PRESSURE_01", "pressure", "bedroom", "empty")
print("MQTT test passed.")
