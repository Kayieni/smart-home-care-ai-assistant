# Scenario Validation Results

> Records AI pipeline output across implementation versions.

---

## Version 0.1 — Instant Mode (scenarios.py)

Events published to MQTT only — no SQLite storage, no timeline compression.

### Results Summary

| Scenario | Activities Detected | Alerts | Notes |
|---|---|---|---|
| Normal Day | `cooking_risk`, `hygiene`, `leaving_home`, `medication_taken` | `[HIGH] stove_unattended` | False positive — reset sends stove=on before off |
| Decline | `cooking_risk`, `leaving_home`, `hygiene` | `[HIGH] stove_unattended`, `[MEDIUM] medication_missed` | Correct medication alert |
| Hazard | `leaving_home`, `hygiene`, `cooking_risk` | `[HIGH] stove_unattended`, `[MEDIUM] medication_missed` | Correct |

### Sample LLM Report — Normal Day v0.1
> Today the resident appeared active and engaged with their daily routine, including cooking a meal. However, the stove was left unattended while the front door was open, indicating a potential risk. This high-severity risk requires extra precautions.

---

## Version 0.2 — Timeline Mode (timeline.py)

Full-day simulated timeline. Events stored in SQLite. Safety Auditor runs hourly 07:00–23:00.

### Improvements vs v0.1

| Area | v0.1 | v0.2 |
|---|---|---|
| Data storage | MQTT only | MQTT + SQLite |
| Time model | Instant snapshot | Full-day timeline |
| Auditor | Single pass | Hourly (07:00–23:00) |
| Inactivity detection | ❌ | ✅ (3h window) |
| Night exit | ❌ | ✅ (23:00–05:00) |
| Sensors | 10 | 15 |
| LLM integration | Narrator only | Auditor + Narrator |

---

## Version 0.3 — Final Implementation

### New Features

| Feature | File | Description |
|---|---|---|
| Sensor model loader | `ai/sensor_model_loader.py` | Single source of truth for all sensor lists |
| Sensors SQLite table | `ai/storage.py` | Sensor catalogue stored in DB, seeded on `init_db()` |
| Consistent MQTT schema | `simulator/mqtt_client.py` | Both modes publish `_meta` and store to SQLite |
| LLM Care Plan audit | `ai/safety_auditor.py` | Sensor catalogue injected into every LLM prompt |
| Caregiver Q&A loop | `ai/narrator.py` | `caregiver_qa_loop()` — interactive session after report |
| Streamlit dashboard | `dashboard.py` | 3-tab UI: Alerts, Chat, Sensor Catalogue |
| Scheduled auditor loop | `run_auditor_loop.py` | Simulated replay or live 60s polling |

### Care Plan Rules Coverage

| Rule | Python Layer | LLM Layer | Dashboard |
|---|---|---|---|
| R01 Medication by 10:00 | ✅ | ✅ | ✅ |
| R02 Hand wash after toilet | ✅ | ✅ | ✅ |
| R03 Hand wash after cooking | ❌ (delegated to LLM) | ✅ | ✅ |
| R04 Daily toilet use | ✅ | ✅ | ✅ |
| R05 Stove unattended | ✅ | ✅ | ✅ |
| R06 Fridge left open | ✅ | ✅ | ✅ |
| R07 Water heater timeout | ✅ | ✅ | ✅ |
| R08 Night exit | ✅ | ✅ | ✅ |
| R09 Inactivity 3h | ✅ | ✅ | ✅ |
