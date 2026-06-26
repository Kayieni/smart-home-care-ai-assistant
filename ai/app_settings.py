"""
app_settings.py
----------------
Loads config/settings.json and exposes named constants.
Import from any module in ai/ or simulator/.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "settings.json")

with open(_PATH, "r") as _f:
    _s = json.load(_f)

# Simulation
TIME_SCALE = _s["simulation"]["time_scale_seconds_per_hour"]

# Auditor
POLL_INTERVAL_SECONDS      = _s["auditor"]["poll_interval_seconds"]
SIMULATED_START_HOUR       = _s["auditor"]["simulated_start_hour"]
SIMULATED_END_HOUR         = _s["auditor"]["simulated_end_hour"]
INACTIVITY_THRESHOLD_HOURS = _s["auditor"]["inactivity_threshold_hours"]

# LLM
OLLAMA_URL   = _s["llm"]["ollama_url"]
OLLAMA_MODEL = _s["llm"]["ollama_model"]
LLM_TIMEOUT  = _s["llm"]["request_timeout_seconds"]
