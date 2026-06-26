"""
Caregiver Dashboard — The Invisible Caregiver
----------------------------------------------
Run with:  streamlit run dashboard.py

Features:
  • Live alert feed — auto-refreshes every 10s while the auditor loop runs
  • Severity metrics (critical / high / medium counts)
  • Full alert log with colour-coded severity badges
  • On-demand chat: ask natural language questions about the resident's day
"""

import sys
import os
import json
import datetime
import time

import streamlit as st

# ---------------------------------------------------------------------------
# Path so we can import from ai/
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai"))

from llm_reporter import answer_question, generate_report
from narrator import build_daily_summary
from storage import init_db
from sensor_model_loader import SENSORS as _ALL_SENSORS

init_db()  # ensure sensors table is seeded

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT       = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(ROOT, "data")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_COLOR = {
    "critical": "#c0392b",
    "high":     "#e67e22",
    "medium":   "#f1c40f",
    "low":      "#2ecc71",
}
SEVERITY_ICON = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🟢",
}

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_alerts() -> list:
    if not os.path.exists(ALERTS_FILE):
        return []
    try:
        with open(ALERTS_FILE, "r") as f:
            data = json.load(f)
        return sorted(data, key=lambda a: (SEVERITY_ORDER.get(a.get("severity", "low").lower(), 9),
                                           a.get("timestamp", "")))
    except Exception:
        return []


def load_summary(date: str) -> dict | None:
    path = os.path.join(DATA_DIR, f"summary_{date}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def available_dates() -> list[str]:
    dates = []
    if os.path.exists(DATA_DIR):
        for fname in os.listdir(DATA_DIR):
            if fname.startswith("summary_") and fname.endswith(".json"):
                dates.append(fname[8:-5])
    return sorted(dates, reverse=True)


def load_sensors() -> list:
    try:
        return [
            {
                "sensor_id":    s["sensor_id"],
                "type":         s["type"],
                "location":     s["location"],
                "activity":     s.get("activity", ""),
                "risk_category": s.get("risk_category", ""),
                "value_format": s.get("value_format", ""),
                "value_info":   (
                    f"1={s['value_map']['1']}, 0={s['value_map']['0']}"
                    if s.get("value_format") == "boolean"
                    else s.get("unit", "")
                ),
            }
            for s in _ALL_SENSORS
        ]
    except Exception:
        return []

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Invisible Caregiver",
    page_icon="🏠",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS — minimal, functional
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .alert-card {
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-left: 5px solid;
        background: #1e1e2e;
        font-size: 0.9rem;
    }
    .badge {
        display: inline-block;
        padding: 2px 9px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        color: #fff;
        text-transform: uppercase;
        margin-right: 8px;
    }
    .metric-box {
        text-align: center;
        border-radius: 10px;
        padding: 18px 10px;
        color: white;
        font-weight: 700;
    }
    .stChatMessage { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("## 🏠 Invisible Caregiver — Dashboard")
st.caption(f"Last refreshed: {datetime.datetime.now().strftime('%H:%M:%S')}")

# ---------------------------------------------------------------------------
# Sidebar — controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Controls")

    auto_refresh = st.toggle("Auto-refresh (live mode)", value=False)
    refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 10, disabled=not auto_refresh)

    st.divider()
    st.markdown("### 📅 Date")
    dates = available_dates()
    if dates:
        selected_date = st.selectbox("View summary for:", dates)
    else:
        selected_date = datetime.date.today().isoformat()
        st.info("No summaries found. Run a simulation first.")

    st.divider()
    if st.button("🔄 Refresh now"):
        st.rerun()

    st.divider()
    st.markdown("### ℹ️ How to use")
    st.markdown("""
1. Run simulation:
   ```
   python run_simulation.py
   ```
2. For live monitoring:
   ```
   python run_auditor_loop.py --live
   ```
3. Enable **Auto-refresh** above to see live alerts.
""")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
alerts   = load_alerts()
summary  = load_summary(selected_date)
sensors  = load_sensors()

# Filter alerts to the selected date
date_alerts = [a for a in alerts if a.get("timestamp", "").startswith(selected_date)]

critical_count = sum(1 for a in date_alerts if a.get("severity", "").lower() == "critical")
high_count     = sum(1 for a in date_alerts if a.get("severity", "").lower() == "high")
medium_count   = sum(1 for a in date_alerts if a.get("severity", "").lower() == "medium")
low_count      = sum(1 for a in date_alerts if a.get("severity", "").lower() == "low")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_alerts, tab_chat, tab_sensors = st.tabs(["🚨 Alerts", "💬 Ask the Assistant", "📡 Sensor Catalogue"])

# ===== TAB 1: Alerts =====
with tab_alerts:
    st.markdown(f"### Alerts — {selected_date}")

    # Severity metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class="metric-box" style="background:{SEVERITY_COLOR['critical']}">
            <div style="font-size:1.8rem">{critical_count}</div>
            <div>Critical</div></div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="metric-box" style="background:{SEVERITY_COLOR['high']}">
            <div style="font-size:1.8rem">{high_count}</div>
            <div>High</div></div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="metric-box" style="background:{SEVERITY_COLOR['medium']}; color:#222">
            <div style="font-size:1.8rem">{medium_count}</div>
            <div>Medium</div></div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""<div class="metric-box" style="background:{SEVERITY_COLOR['low']}; color:#222">
            <div style="font-size:1.8rem">{low_count}</div>
            <div>Low</div></div>""", unsafe_allow_html=True)

    st.markdown("")

    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        if not date_alerts:
            st.success("✅ No alerts for this date. The resident appears to be doing well.")
        else:
            selected_severities = st.multiselect(
                "Filter by severity",
                options=["critical", "high", "medium", "low"],
                default=["critical", "high", "medium", "low"],
            )
            # Primary: severity asc (critical first), secondary: timestamp desc (latest first)
            filtered = sorted(
                [a for a in date_alerts if a.get("severity") in selected_severities],
                key=lambda a: (
                    SEVERITY_ORDER.get(a.get("severity", "low"), 4),
                    [-ord(c) for c in a.get("timestamp", "")],
                ),
            )
            for alert in filtered:
                sev  = alert.get("severity", "low")
                icon = SEVERITY_ICON.get(sev, "⚪")
                col  = SEVERITY_COLOR.get(sev, "#888")
                ts   = alert.get("timestamp", "")
                time_str = ts[11:16] if len(ts) >= 16 else ts
                risk = alert.get("risk", "unknown").replace("_", " ").title()
                reason = alert.get("reason", "")
                st.markdown(f"""
<div class="alert-card" style="border-color:{col}">
  <span class="badge" style="background:{col}">{icon} {sev}</span>
  <strong>{risk}</strong>
  <span style="color:#888; font-size:0.8rem; float:right">{time_str}</span><br>
  <span style="color:#ccc">{reason}</span>
</div>
""", unsafe_allow_html=True)

    with right_col:
        if summary:
            st.markdown("#### 📋 Activity Summary")
            activities = summary.get("activities_detected", [])
            activity_labels = {
                "wake_up": "🛏️ Woke up",
                "hygiene": "🧼 Hygiene routine",
                "eating": "🍽️ Ate / opened fridge",
                "medication_taken": "💊 Took medication",
                "cooking_risk": "🔥 Used stove",
                "leaving_home": "🚪 Left home",
                "toilet_use": "🚽 Used toilet",
                "water_heater_used": "🚿 Shower",
                "balcony_visit": "🌿 Visited balcony",
                "plant_watering": "💧 Watered plants",
            }
            if activities:
                for act in activities:
                    st.markdown(f"- {activity_labels.get(act, act)}")
            else:
                st.info("No activities detected for this date.")

            st.divider()
            st.markdown("#### 📊 Event Timeline")
            timeline = summary.get("timeline", [])
            if timeline:
                import pandas as pd
                df = pd.DataFrame(timeline)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No events in timeline.")

# ===== TAB 2: Chat =====
with tab_chat:
    st.markdown("### 💬 Ask About the Resident")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_summary" not in st.session_state:
        st.session_state.chat_summary = None

    if summary:
        st.session_state.chat_summary = summary
    elif st.session_state.chat_summary is None:
        st.info("No summary loaded — run a simulation first to enable chat.")

    with st.expander("💡 Example questions", expanded=True):
        examples = [
            "Did Maria have a healthy morning?",
            "Did she take her medication today?",
            "Was there any dangerous event today?",
            "How was her day overall?",
            "Did she eat today?",
            "Did she leave the house?",
        ]
        ex_cols = st.columns(3)
        for i, ex in enumerate(examples):
            if ex_cols[i % 3].button(ex, key=f"ex_{ex}", use_container_width=True):
                st.session_state.pending_question = ex

    chat_container = st.container(height=420)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    pending = st.session_state.get("pending_question", None)
    if pending:
        del st.session_state["pending_question"]

    user_input = st.chat_input("Ask a question about today's activity…")
    question = pending or user_input

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(question)
        if st.session_state.chat_summary:
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking…"):
                        answer = answer_question(question, st.session_state.chat_summary)
                    st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            no_data = "I don't have any data for this date yet. Please run a simulation first."
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(no_data)
            st.session_state.messages.append({"role": "assistant", "content": no_data})

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ===== TAB 3: Sensor Catalogue =====
with tab_sensors:
    st.markdown("### 📡 Installed Sensor Catalogue")
    st.caption("Loaded from the SQLite `sensors` table — seeded from config/sensor_model.json")

    if not sensors:
        st.warning("No sensors found. Run any simulation to initialise the database.")
    else:
        # Summary counts by category
        categories = {}
        for s in sensors:
            cat = s["risk_category"] or "other"
            categories[cat] = categories.get(cat, 0) + 1
        cat_cols = st.columns(len(categories))
        cat_colors = {"safety": "#e74c3c", "hygiene": "#3498db", "health": "#2ecc71",
                      "movement": "#9b59b6", "activity": "#f39c12", "other": "#95a5a6"}
        for i, (cat, count) in enumerate(sorted(categories.items())):
            col_hex = cat_colors.get(cat, "#888")
            cat_cols[i].markdown(
                f"""<div class="metric-box" style="background:{col_hex}; font-size:0.85rem">
                <div style="font-size:1.5rem">{count}</div><div>{cat.title()}</div></div>""",
                unsafe_allow_html=True
            )

        st.markdown("")

        # Filter by category
        all_cats = sorted({s["risk_category"] for s in sensors})
        sel_cats = st.multiselect("Filter by category", options=all_cats, default=all_cats)
        filtered_sensors = [s for s in sensors if s["risk_category"] in sel_cats]

        import pandas as pd
        df = pd.DataFrame(filtered_sensors).rename(columns={
            "sensor_id": "Sensor ID",
            "type": "Type",
            "location": "Location",
            "activity": "Activity",
            "risk_category": "Category",
            "value_format": "Format",
            "value_info": "Values",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### Last Known State per Sensor")
        st.caption("Most recent value recorded in the events table for each sensor.")
        if summary and summary.get("timeline"):
            # Build last-state from timeline
            last_state = {}
            for e in summary["timeline"]:
                last_state[e["sensor"]] = {"time": e["time"], "value": e["value"]}
            state_rows = [
                {"Sensor ID": sid, "Last Value": v["value"], "At": v["time"]}
                for sid, v in sorted(last_state.items())
            ]
            st.dataframe(pd.DataFrame(state_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No event data for the selected date.")

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

