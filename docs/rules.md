# Care Plan Rules

> Defined in `config/rules.json` · Enforced by `ai/safety_auditor.py` (Python layer) and injected into the LLM Safety Auditor prompt.

## Activity Detection Rules

| Activity | Trigger Condition | Sensors Involved |
|---|---|---|
| `wake_up` | Bed pressure → `empty` | `BED_PRESSURE_01`, `BEDROOM_PIR_01` |
| `hygiene` | Water flow detected **and** soap used | `BATH_WATER_01`, `SOAP_VIB_01` |
| `eating` | Fridge opened | `FRIDGE_DOOR_01`, `KITCHEN_PIR_01` |
| `medication_taken` | Medicine box vibration detected | `MED_BOX_01` |
| `cooking_risk` | Stove smart plug → `on` | `STOVE_POWER_01`, `OVEN_TEMP_01` |
| `leaving_home` | Front door → `open` then `closed` | `DOOR_CONTACT_01`, `HALLWAY_PIR_01` |
| `toilet_use` | Toilet occupancy → `occupied` | `TOILET_OCCUPANCY_01` |
| `water_heater_used` | Water heater plug → `on` | `WATER_HEATER_01` |
| `balcony_visit` | Balcony PIR → `motion` | `BALCONY_PIR_01` |
| `plant_watering` | Soil moisture reading recorded | `SOIL_MOISTURE_01` |

---

## Safety Alert Rules

| Rule ID | Description | Severity | Python Rule | Window |
|---|---|---|---|---|
| R01 | Medication not taken by 10:00 AM | `medium` | RULE 3 | Hourly from 10:00 |
| R02 | Hands not washed after toilet visit | `medium` | RULE 8 | 1h window |
| R03 | Hands not washed after cooking | `medium` | LLM layer | 1h window |
| R04 | No toilet use detected all day | `high` | RULE 9 | Check at 21:00 |
| R05 | Stove on + door open (left while cooking) | `critical` | RULE 1 & 2 | 1h window |
| R06 | Fridge door left open (no close event) | `low` | RULE 7 | 1h window |
| R07 | Water heater on 2+ hours without off event | `medium` | RULE 6 | 2h window |
| R08 | Front door opened between 23:00–05:00 | `high` | RULE 5 | 1h window (open event) |
| R09 | No movement for 3+ consecutive hours (09:00–21:00) | `medium` | RULE 4 | 3h window |

---

## Alert Output Schema

Every alert written to `data/alerts.json` follows this structure:

```json
{
  "timestamp": "2026-06-25T09:00:00",
  "risk":      "medication_missed",
  "severity":  "medium",
  "reason":    "Medication box not interacted with by 09:00."
}
```

**Severity levels:** `critical` > `high` > `medium` > `low`

## Activity
hygiene	water flow + soap vibration
eating	fridge open + kitchen motion
medication	medicine box vibration
cooking	stove ON
leaving_home	door open + hallway motion


1. Hygiene — Wash hands after toilet (A)
Sensors:
Toilet occupancy sensor
Water flow sensor (sink)
Soap vibration sensor
Rule:
IF toilet_used
AND water_flow_detected
AND soap_used
→ hygiene_completed
Risk if NOT satisfied:
hygiene_missing

2. Kitchen Safety — Stove/Oven monitoring (A)
Sensors:
Smart plug (stove/oven)
Temperature sensor
Rule:
IF stove_power == ON
AND no_motion_in_kitchen FOR > X minutes
→ cooking_risk
IF stove_power == ON
AND resident_location != kitchen
→ hazard_stove_left_on

3. Door Exit Monitoring (A)
Sensors:
Door contact sensor
Hallway motion sensor
Rule:
IF door_open
AND time BETWEEN 00:00–05:00
→ night_exit_risk
IF door_open
AND hallway_motion_detected
→ leaving_home

4. Bed Exit / Wake-up (A)
Sensors:
Bed pressure sensor
Bedroom PIR motion
Rule:
IF bed_pressure == empty
AND bedroom_motion == true
→ wake_up

5. Medication intake (A)
Sensors:
Medicine box vibration sensor
Rule:
IF medicine_box_vibration_detected
→ medication_taken
Risk:
IF time > scheduled_medication_time
AND no_vibration_detected
→ medication_missed

6. Water heater left ON (B)
Sensors:
Smart plug (heater)
Rule:
IF water_heater_power == ON
AND duration > threshold (e.g. 30 min)
→ heater_risk

7. Fridge usage monitoring (B)
Sensors:
Fridge contact sensor
Kitchen motion sensor
Rule:
IF fridge_open
AND kitchen_motion_detected
→ eating_activity
IF fridge_open_duration > threshold
→ fridge_left_open_risk

8. Balcony activity — watering plants (C)
Sensors:
Balcony PIR
Soil moisture sensor
Rule:
IF balcony_motion_detected
AND soil_moisture_increases
→ plant_watering