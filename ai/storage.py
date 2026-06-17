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
    """Create the events table if it does not exist."""
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
        conn.commit()


def store_event(simulated_ts: str, sensor_id: str, sensor_type: str, location: str, value: str):
    """Insert a single sensor event into the database."""
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO events (simulated_ts, sensor_id, sensor_type, location, value) VALUES (?, ?, ?, ?, ?)",
            (simulated_ts, sensor_id, sensor_type, location, value)
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
    Return all events for a given date (YYYY-MM-DD).
    """
    from_ts = f"{base_date}T00:00:00"
    to_ts   = f"{base_date}T23:59:59"
    return get_events_in_window(from_ts, to_ts)


def clear_events():
    """Wipe all stored events — use before each simulation run."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM events")
        conn.commit()
    print("[storage] Events cleared.")


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
