# Sensor Catalogue

> Defined in `config/sensor_model.json` · Loaded into SQLite `sensors` table via `ai/storage.py` · Accessible at runtime via `ai/sensor_model_loader.py`

## Priority A — Core Sensors

| Sensor ID | Type | Location | Activity | Risk Category | Possible Values |
|---|---|---|---|---|---|
| `BED_PRESSURE_01` | Pressure mat | Bedroom — bed | Sleep / Wake | Movement | `occupied`, `empty` |
| `BEDROOM_PIR_01` | PIR motion | Bedroom | Movement | Movement | `motion`, `no_motion` |
| `TOILET_OCCUPANCY_01` | Occupancy | Bathroom — toilet | Toilet use | Hygiene | `occupied`, `empty` |
| `BATH_WATER_01` | Water flow | Bathroom — sink | Hand washing | Hygiene | `flow`, `no_flow` |
| `SOAP_VIB_01` | Vibration | Soap dispenser | Hand washing | Hygiene | `used`, `not_used` |
| `STOVE_POWER_01` | Smart plug | Kitchen — stove | Cooking | Safety | `on`, `off` |
| `OVEN_TEMP_01` | Temperature | Kitchen — oven | Cooking | Safety | numeric (°C) |
| `MED_BOX_01` | Vibration | Medicine box | Medication | Health | `used`, `not_used` |
| `DOOR_CONTACT_01` | Contact | Entrance — front door | Exit home | Safety | `open`, `closed` |
| `HALLWAY_PIR_01` | PIR motion | Hallway | Movement | Movement | `motion`, `no_motion` |

## Priority B — Supporting Sensors

| Sensor ID | Type | Location | Activity | Risk Category | Possible Values |
|---|---|---|---|---|---|
| `WATER_HEATER_01` | Smart plug | Bathroom — water heater | Utility usage | Safety | `on`, `off` |
| `FRIDGE_DOOR_01` | Contact | Kitchen — fridge | Eating | Activity | `open`, `closed` |
| `KITCHEN_PIR_01` | PIR motion | Kitchen | Movement | Activity | `motion`, `no_motion` |

## Priority C — Leisure / Wellbeing Sensors

| Sensor ID | Type | Location | Activity | Risk Category | Possible Values |
|---|---|---|---|---|---|
| `BALCONY_PIR_01` | PIR motion | Balcony | Leisure | Activity | `motion`, `no_motion` |
| `SOIL_MOISTURE_01` | Soil moisture | Balcony — plant pots | Plant watering | Activity | numeric (%) |

---

## Placement Justification

| Sensor | Why this type? | Why this location? |
|---|---|---|
| `BED_PRESSURE_01` | Passive — no resident interaction required | Under mattress — detects bed occupancy without line of sight |
| `SOAP_VIB_01` | Confirms dispenser was pressed — water flow alone does not prove soap was used | Mounted on dispenser body |
| `TOILET_OCCUPANCY_01` | Triggers post-visit hand-wash compliance check | Under toilet seat or door beam |
| `MED_BOX_01` | Detects any box movement — more reliable than contact sensor | Attached to medication box |
| `STOVE_POWER_01` | Captures electrical intent (switch), not just heat | Power socket of stove |
| `OVEN_TEMP_01` | Confirms active cooking and detects abnormal temperatures | Oven exterior surface |
| `WATER_HEATER_01` | Detects forgotten appliance without resident interaction | Power socket of water heater |
| `DOOR_CONTACT_01` | Binary, low-power, instant exit detection | Door frame, entrance |
| `SOIL_MOISTURE_01` | Confirms watering without requiring resident device interaction | Inserted in pot soil |

---

## Data Schemas

### MQTT Telemetry Packet (ThingsBoard)

```json
{
  "<sensor_id>": "<value>",
  "_meta": {
    "sensor_id":    "FRIDGE_DOOR_01",
    "type":         "contact",
    "location":     "kitchen_fridge",
    "simulated_ts": "2026-06-25T08:00:00"
  }
}
```

### SQLite `events` Table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment row ID |
| `simulated_ts` | TEXT | ISO 8601 timestamp |
| `sensor_id` | TEXT | Sensor identifier |
| `sensor_type` | TEXT | Physical sensor type |
| `location` | TEXT | Physical location |
| `value` | TEXT | Sensor reading |

### SQLite `sensors` Table

| Column | Type | Description |
|---|---|---|
| `sensor_id` | TEXT PK | Unique sensor identifier |
| `type` | TEXT | Physical sensor type |
| `location` | TEXT | Deployment location |
| `activity` | TEXT | Associated activity |
| `risk_category` | TEXT | Risk domain |
| `possible_values` | TEXT | Comma-separated valid values |
