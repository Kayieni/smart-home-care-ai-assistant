"""
Event Storage Layer
-------------------
Stores all sensor events in a local SQLite database.
Provides functions to insert events and query by time window.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "events.db")


def _get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create all tables if they do not exist, and seed the sensors table."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                simulated_ts TEXT NOT NULL,
                sensor_id   TEXT NOT NULL,
                sensor_type TEXT,
                location    TEXT,
                value       TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensors (
                sensor_id      TEXT PRIMARY KEY,
                type           TEXT NOT NULL,
                location       TEXT NOT NULL,
                activity       TEXT,
                risk_category  TEXT,
                value_format   TEXT,
                value_info     TEXT
            )
        """)
        conn.commit()
    _seed_sensors()


def _seed_sensors():
    """Populate the sensors table from sensor_model.json (upsert — safe to call repeatedly)."""
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "sensor_model.json")
    with open(model_path, "r") as f:
        sensors = json.load(f)["sensors"]
    with _get_connection() as conn:
        for s in sensors:
            if s.get("value_format") == "boolean":
                vm = s.get("value_map", {})
                value_info = f"1={vm.get('1','on')}, 0={vm.get('0','off')}"
            else:
                value_info = s.get("unit", "")
            conn.execute("""
                INSERT OR REPLACE INTO sensors
                    (sensor_id, type, location, activity, risk_category, value_format, value_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                s["sensor_id"],
                s["type"],
                s["location"],
                s.get("activity", ""),
                s.get("risk_category", ""),
                s.get("value_format", ""),
                value_info
            ))
        conn.commit()


def get_all_sensors() -> list:
    """Return all sensor definitions from the sensors table."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT sensor_id, type, location, activity, risk_category, value_format, value_info FROM sensors ORDER BY risk_category, sensor_id"
        )
        rows = cursor.fetchall()
    return [
        {
            "sensor_id":     r[0],
            "type":          r[1],
            "location":      r[2],
            "activity":      r[3],
            "risk_category": r[4],
            "value_format":  r[5],
            "value_info":    r[6],
        }
        for r in rows
    ]


def store_event(simulated_ts: str, sensor_id: str, sensor_type: str, location: str, value: str):
    """Insert a single sensor event into the database."""
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO events (simulated_ts, sensor_id, sensor_type, location, value) VALUES (?, ?, ?, ?, ?)",
            (simulated_ts, sensor_id, sensor_type, location, str(value))
        )
        conn.commit()


def get_events_in_window(from_ts: str, to_ts: str) -> list:
    """
    Return all events with simulated_ts between from_ts and to_ts (ISO strings).
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT simulated_ts, sensor_id, sensor_type, location, value FROM events WHERE simulated_ts >= ? AND simulated_ts <= ? ORDER BY simulated_ts ASC",
            (from_ts, to_ts)
        )
        rows = cursor.fetchall()

    return [
        {
            "simulated_ts": r[0],
            "sensor_id":    r[1],
            "sensor_type":  r[2],
            "location":     r[3],
            "value":        r[4]
        }
        for r in rows
    ]


def get_all_events_today(base_date: str) -> list:
    """
    Return all events for a given simulation day (YYYY-MM-DD).
    Includes early-morning hours of the following day (up to 05:59:59)
    to capture overnight events such as night-time exits (hour 27 = next-day 03:00).
    """
    from datetime import datetime as _dt, timedelta as _td
    from_ts  = f"{base_date}T00:00:00"
    next_day = (_dt.strptime(base_date, "%Y-%m-%d") + _td(days=1)).strftime("%Y-%m-%d")
    to_ts    = f"{next_day}T05:59:59"
    return get_events_in_window(from_ts, to_ts)


def clear_events(dates: list):
    """Delete stored events for the given simulation dates only (YYYY-MM-DD strings).
    Preserves historical data from other days so the narrator can query past runs."""
    with _get_connection() as conn:
        for date in dates:
            conn.execute("DELETE FROM events WHERE simulated_ts LIKE ?", (f"{date}%",))
        conn.commit()
    print(f"[storage] Events cleared for: {', '.join(dates)}")


# ---------------------------------------------------------------------------
# WINDOWING
# ---------------------------------------------------------------------------

def get_window(anchor_ts: str, hours: int) -> list:
    """
    Return events in the [anchor_ts - hours, anchor_ts] window.
    anchor_ts: ISO string (e.g. "2026-06-17T09:00:00")
    hours: how many hours back to look
    """
    anchor = datetime.fromisoformat(anchor_ts)
    from_dt = anchor - __import__('datetime').timedelta(hours=hours)
    return get_events_in_window(from_dt.isoformat(), anchor_ts)


def get_latest_sensor_states(events: list) -> dict:
    """
    Given a list of events, return the most recent value per sensor_id.
    This builds the current 'state snapshot' of the apartment.
    """
    state = {}
    for e in events:
        state[e["sensor_id"]] = e["value"]
    return state
