# The Invisible Caregiver
**CEID_NE576 Ubiquitous Computing** — Smart home assisted living system for elderly care using IoT sensors, MQTT, ThingsBoard Cloud, and a local AI reasoning engine.

## System Architecture

```
Sensor Simulator → MQTT (Mosquitto) → ThingsBoard Cloud
                                              ↓
                                      AI Pipeline (local)
                                      ├── Activity Engine  (rule-based)
                                      ├── Safety Engine    (risk detection)
                                      └── LLM Reporter     (Ollama / template)
```

## Project Structure

```
simulator/      — IoT sensor simulation and MQTT publishing
ai/             — Activity recognition, risk detection, caregiver report generation
sensors/        — Digital twin sensor model (sensor_model.json)
docs/           — Design documentation and scenario validation
```

## Running the System

**Simulate a scenario and publish to ThingsBoard:**
```bash
python -m simulator.runner
```

**Run the AI pipeline (fetch → reason → report):**
```bash
python -m ai.main_ai
```

## Scenarios

| Scenario | Description |
|---|---|
| 1 — Normal | Resident completes full daily routine without issues |
| 2 — Decline | Resident misses medication (early decline pattern) |
| 3 — Hazard | Stove left on while resident exits (immediate safety risk) |

## Requirements

```bash
pip install paho-mqtt requests ollama
```

Ollama must be running locally with `llama3.2` pulled:
```bash
ollama pull llama3.2
```

## Configuration

Copy `.env.example` to `.env` and fill in your ThingsBoard credentials.
The system also works with hardcoded fallback values for local development.

