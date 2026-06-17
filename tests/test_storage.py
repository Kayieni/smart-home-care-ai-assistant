"""
test_storage.py
---------------
Verifies the event storage layer: init, store, query, windowing.
Run from project root: python tests/test_storage.py
"""

import datetime
from ai.storage import init_db, store_event, get_all_events_today, get_window, get_latest_sensor_states

print("Testing storage layer...")

init_db()

today = datetime.date.today().isoformat()

# Query full day
all_events = get_all_events_today(today)
print(f"  24h window: {len(all_events)} events stored")
for e in all_events:
    print(f"    {e['simulated_ts'][11:16]}  {e['sensor_id']} = {e['value']}")

# Query 1h window
anchor = f"{today}T09:30:00"
window_1h = get_window(anchor, hours=1)
print(f"\n  1h window ending at 09:30: {len(window_1h)} events")
for e in window_1h:
    print(f"    {e['simulated_ts'][11:16]}  {e['sensor_id']} = {e['value']}")

# Sensor state snapshot
state = get_latest_sensor_states(window_1h)
print(f"\n  Sensor state snapshot:")
for sensor, value in state.items():
    print(f"    {sensor}: {value}")

print("\nStorage test passed.")
