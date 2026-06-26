# Simulation Scenarios

> Defined in `simulator/timeline.py` · Entry point: `python run_simulation.py`

Three scenarios of increasing danger simulate a full day in the resident's apartment.
Each event is published to ThingsBoard via MQTT **and** stored in the local SQLite `events` database.

---

## Scenario 1 — Normal Day

A complete, healthy daily routine. All Care Plan rules satisfied. Expected: **zero alerts**.

| Time | Sensor Event | Inferred Activity |
|---|---|---|
| 07:00 | `BED_PRESSURE_01` → `empty` | Wake-up |
| 07:10–07:22 | `TOILET_OCCUPANCY_01` occupied/empty + `BATH_WATER_01` flow + `SOAP_VIB_01` used | Toilet visit + hand wash |
| 07:23–07:55 | `WATER_HEATER_01` on → off | Shower |
| 08:00–08:14 | `FRIDGE_DOOR_01` open/closed + hand wash | Breakfast + hygiene |
| 09:00 | `MED_BOX_01` → `used` | Morning medication taken ✅ |
| 12:00–12:08 | `FRIDGE_DOOR_01` open/closed + `KITCHEN_PIR_01` | Lunch |
| 14:00–14:35 | `BALCONY_PIR_01` motion + `SOIL_MOISTURE_01` 65% | Balcony + plant watering |
| 18:05–18:41 | `STOVE_POWER_01` on → off + hand wash | Dinner + hygiene |
| 21:30 | `MED_BOX_01` → `used` | Evening medication taken ✅ |
| 22:00 | `BED_PRESSURE_01` → `occupied` | Bedtime |

---

## Scenario 2 — Subtle Decline

Early-stage cognitive decline. Danger signs are subtle and accumulate over the day.

| Time | Sensor Event | Significance |
|---|---|---|
| 08:00 | `BED_PRESSURE_01` → `empty` | Late wake-up (1h late) |
| 08:30 | `SOAP_VIB_01` → `not_used`, no toilet event | Skipped morning hygiene ⚠️ |
| 09:00–09:15 | `FRIDGE_DOOR_01` open, closed 15 min later | Fridge left open ⚠️ (R06) |
| 09:30 | `MED_BOX_01` → `not_used` | Medication not taken ❌ (R01) |
| 09:30–15:30 | No PIR events | **6-hour inactivity gap** ❌ (R09 ×6) |
| 15:30 | Single fridge opening | Only one meal all day ⚠️ |
| 23:00 | `BED_PRESSURE_01` → `occupied` | Late bedtime |

**Expected alerts:** `medication_missed` (medium), `inactivity` ×6 (medium), `fridge_left_open` (low)

---

## Scenario 3 — Acute Hazard

Multiple simultaneous critical safety threats.

| Time | Sensor Event | Hazard |
|---|---|---|
| 07:00–07:22 | Normal morning routine | — |
| 07:23 | `WATER_HEATER_01` → `on` (never turned off) | Forgotten appliance ⚠️ (R07) |
| 08:00–08:08 | `FRIDGE_DOOR_01` open/closed | Breakfast |
| 08:30 | `MED_BOX_01` → `used` | Morning medication taken ✅ |
| 12:00–12:08 | `FRIDGE_DOOR_01` open/closed | Lunch prep started |
| 12:10 | `STOVE_POWER_01` → `on`, `OVEN_TEMP_01` → 80°C | Cooking started (low temp) |
| 12:15 | `DOOR_CONTACT_01` → `open`, `HALLWAY_PIR_01` → `motion` | **Resident leaves while cooking** 🔴 (R05) |
| 12:17 | `DOOR_CONTACT_01` → `closed` | Door shut behind them |
| 13:30 | `OVEN_TEMP_01` → 210°C | **Nobody home — critical temperature** 🔴 |
| 15:30 | `DOOR_CONTACT_01` → `open` | Resident returns home |
| 15:31 | `DOOR_CONTACT_01` → `closed` | Door shut |
| 15:35 | `STOVE_POWER_01` → `off` | Resident turns stove off |
| 21:00 | `MED_BOX_01` → `used` | Evening medication taken ✅ |
| 03:00 (next day) | `DOOR_CONTACT_01` → `open`, `HALLWAY_PIR_01` → `motion` | **Night-time exit** 🔴 (R08) |
| 03:02 (next day) | `DOOR_CONTACT_01` → `closed` | Door shut — resident outside at 3 AM |

**Expected alerts:** `stove_unattended` (critical), `stove_on` (high ×3), `night_exit` (high), `water_heater_on` (medium)
