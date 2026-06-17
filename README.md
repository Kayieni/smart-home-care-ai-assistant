# The Invisible Caregiver
**CEID_NE576 Ubiquitous Computing** — Smart home assisted living system for elderly care using IoT sensors, MQTT, ThingsBoard Cloud, and a local AI reasoning engine.

## System Architecture

```
[config/]           rules.json, sensor_model.json
      ↓
[simulator/]        timeline.py ──► mqtt_client.py ──► ThingsBoard Cloud
      ↓                        ──► storage.py ──► data/events.db
[ai/]               activity_engine.py + safety_auditor.py ──► narrator.py
      ↓
[data/]             alerts.json, summary_YYYY-MM-DD.json
```

## Project Structure

```
smart-home-care-ai-assistant/
├── run_simulation.py       — single entry point
├── simulator/              — IoT sensor simulation and MQTT publishing
│   ├── mqtt_client.py
│   ├── timeline.py         — time-series simulation engine
│   ├── scenarios.py        — instant scenario definitions
│   └── runner.py           — interactive launcher (legacy mode)
├── ai/                     — AI reasoning layer
│   ├── activity_engine.py  — rule-based activity detection
│   ├── safety_auditor.py   — 1h window hazard detection
│   ├── narrator.py         — 24h summary + LLM caregiver report
│   ├── storage.py          — SQLite event store + windowing
│   └── llm_reporter.py     — Ollama LLM / template report generator
├── config/                 — configuration files
│   ├── rules.json          — activity label map
│   └── sensor_model.json   — digital twin sensor definitions (15 sensors)
├── data/                   — runtime outputs (gitignored)
├── docs/                   — academic documentation and scenario validation
└── tests/                  — test scripts
    ├── test_mqtt.py
    ├── test_storage.py
    └── test_ai_pipeline.py
```

## Quick Start

**Run a full simulation (single command):**
```bash
python run_simulation.py
```
Choose a scenario (1 / 2 / 3). The system will simulate the full day, store events, run the Safety Auditor, and generate a caregiver report automatically.

## Scenarios

| # | Name | Description |
|---|---|---|
| 1 | Normal Day | Resident completes full daily routine — no alerts |
| 2 | Decline Day | Missed medication + extended inactivity periods |
| 3 | Hazard Day | Stove left on while resident exits — CRITICAL alert |

## Tests

```bash
python tests/test_mqtt.py           # verify MQTT publish to ThingsBoard
python tests/test_storage.py        # verify event storage and windowing
python tests/test_ai_pipeline.py    # verify AI reasoning (run after simulation)
```

## Requirements

```bash
pip install paho-mqtt requests python-dotenv ollama
```

Ollama must be running locally with `llama3.2` pulled:
```bash
ollama pull llama3.2
```
If Ollama is unavailable, the system falls back to a rule-based template report automatically.

## Configuration

Copy `.env.example` to `.env` and fill in your ThingsBoard credentials:
```
TB_JWT_TOKEN=your_thingsboard_jwt_token
TB_DEVICE_ID=your_device_id
MQTT_TOKEN=your_mqtt_device_token
```

JWT tokens expire after ~8 hours — refresh from ThingsBoard Profile → Copy JWT Token.

