import json
import os
import time
import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()  # reads .env file from project root

sys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai")
import sys
sys.path.insert(0, sys_path)
from storage import init_db, store_event

TOKEN = os.environ.get("MQTT_TOKEN")

client = mqtt.Client()
client.username_pw_set(TOKEN)

client.connect("mqtt.eu.thingsboard.cloud", 1883, 60)
client.loop_start()

init_db()


def send(sensor_id, sensor_type, location, value):
    ts = datetime.datetime.now().isoformat(timespec="seconds")

    payload = {
        sensor_id: value,
        "_meta": {
            "sensor_id":    sensor_id,
            "type":         sensor_type,
            "location":     location,
            "simulated_ts": ts
        }
    }

    client.publish(
        "v1/devices/me/telemetry",
        json.dumps(payload)
    )

    store_event(ts, sensor_id, sensor_type, location, value)

    time.sleep(0.5)  # allow network loop to flush the message
    print(f"Sent: {sensor_id} = {value}  (type={sensor_type}, location={location})")
