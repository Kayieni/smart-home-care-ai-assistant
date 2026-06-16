import json
import os
import time
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()  # reads .env file from project root

TOKEN = os.environ.get("MQTT_TOKEN")

client = mqtt.Client()
client.username_pw_set(TOKEN)

client.connect("mqtt.eu.thingsboard.cloud", 1883, 60)
client.loop_start()


def send(sensor_id, sensor_type, location, value):
    payload = {sensor_id: value}

    client.publish(
        "v1/devices/me/telemetry",
        json.dumps(payload)
    )

    time.sleep(0.5)  # allow network loop to flush the message
    print(f"Sent: {sensor_id} = {value}  (type={sensor_type}, location={location})")