import os
import requests
from dotenv import load_dotenv

load_dotenv()  # reads .env file from project root

JWT_TOKEN = os.environ.get("TB_JWT_TOKEN")
DEVICE_ID = os.environ.get("TB_DEVICE_ID")

BASE_URL = "https://eu.thingsboard.cloud"
url = f"{BASE_URL}/api/plugins/telemetry/DEVICE/{DEVICE_ID}/values/timeseries"

headers = {
    "X-Authorization": f"Bearer {JWT_TOKEN}"
}

def get_latest_data():
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()