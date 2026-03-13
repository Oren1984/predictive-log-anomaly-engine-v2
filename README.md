# Predictive Log Anomaly Engine

AI-powered observability and anomaly detection system for software logs.

This project detects risky behavioral patterns in log streams **before full service failure occurs**.  
Instead of reacting only after incidents happen, the engine analyzes event sequences in real time, scores anomalous behavior, generates alerts, and exposes a complete observability stack for investigation.

## Tech Stack

Python • FastAPI • Docker • Prometheus • Grafana • Pytest • GitHub Actions

---

## Overview

Traditional monitoring systems usually detect failures **after** they already impact the system, for example through CPU spikes, crashes, or error bursts.

The **Predictive Log Anomaly Engine** takes a more proactive approach:

- parses and normalizes raw logs
- extracts behavioral templates
- builds event sequences
- applies AI-based anomaly scoring
- generates severity-based alerts
- exposes runtime metrics and dashboards for investigation

The result is a full AI runtime pipeline combined with an observability and alerting layer.

---

## Key Capabilities

- Real-time log anomaly detection using sequence-based analysis
- Runtime inference pipeline for streaming event ingestion
- Severity scoring and alert generation
- FastAPI service with built-in investigation UI
- Prometheus metrics and Grafana dashboards
- Docker-based local deployment
- CI/CD validation with automated tests

---

## System Architecture

The system follows a full runtime pipeline:

```text
Logs
  ↓
Parsing & Template Mining
  ↓
Sequence Builder
  ↓
ML Scoring Engine
  ↓
Alert Manager
  ↓
FastAPI Service
  ↓
Prometheus + Grafana
  ↓
Investigation UI

```

## Main Components
1. Parsing & Template Mining:

   Transforms raw logs into structured templates that reduce noise and preserve behavioral patterns.

2. Sequence Builder:

   Builds event windows and sequences that represent operational behavior over time.

3. ML Scoring Engine:

   Applies anomaly detection logic to detect suspicious or unusual behavior patterns.

4. Alert Manager:

   Generates alerts with severity levels, cooldown handling, and alert lifecycle logic.

5. API Service:

   Exposes ingestion, health, alerts, metrics, and UI-related endpoints through FastAPI.

6. Observability Layer:

   Integrates Prometheus metrics, Grafana dashboards, and health visibility for runtime monitoring.

7. Investigation UI:

   Provides a lightweight read-only interface for reviewing alerts, system state, and future investigation workflows.

---

## Included Observability Features

The project includes an operational observability stack with:

1. Prometheus metrics collection

2. Grafana dashboard provisioning

3. System health visibility

4. Ingest error visibility

5. Alert-oriented monitoring rules

6. Production-style compose override (docker-compose.prod.yml)

---

## Demo UI

The project includes a minimal UI served directly by FastAPI.

The UI is intentionally lightweight and read-only.
Its role is to support observability and investigation, not backend reconfiguration.

Current and planned UI direction:

1. alert review

2. anomaly investigation

3. health inspection

4. future RAG-style investigation assistance

---

## Quick Start

### Build and run
```bash
docker compose build
docker compose up
```

---

## Open the services
- API / UI: http://localhost:8000

- Prometheus: http://localhost:9090

- Grafana: http://localhost:3000

---

## Demo Walkthrough
Step	      Action	               Expected Result
1	         Ingest events	         Synthetic logs enter the runtime pipeline
2	         Open alerts view	      Alerts appear with severity and score
3	         Open dashboard	         Prometheus / Grafana show runtime activity
4	         Query the system	      Investigation-oriented answer is returned

---

## Example Questions

1. How does the alert threshold work?

2. What model is used for anomaly detection?

3. What dataset is used for training?

4. How does the health signal work?

5. How do I run the system with Docker?

---

## Testing
Fast test suite
```bash
pytest -m "not slow"
```

Integration tests
```bash
pytest -m integration
```

---

## Documentation Structure

Additional project documentation is organized under docs/:

1. docs/current_system/ — current architecture, roadmap, UI direction

2. docs/api/ — API reference

3. docs/operations/ — alerts, deployment, metrics, security

4. docs/system_validation/ — audit and validation reports

---

## Project Team

Developed as part of an Applied AI Engineering project.

- **Oren Salami** — DevOps, QA, Core Architecture Design, Technical Specification

- **Dan Kalfon** — Backend Engineering, Core Architecture Design, Technical Specification

- **Nahshon Raizman** — Frontend Development and UI , Core Architecture Design, Technical
                        Specification

- **Jonathan Finkelstein** — Frontend Development and UI , Core Architecture Design, Technical
                             Specification

---

## Project Status

Current repository status:

1. runtime inference pipeline implemented

2. alert pipeline implemented

3. observability stack integrated

4. Grafana and Prometheus configured

5. production-style deployment override added

6. validation and tests passing

7. UI implemented for alert review and investigation workflows

All tests passing (578 tests) and full containerized runtime included.

This repository represents a complete AI engineering prototype with strong emphasis on runtime behavior, observability, and investigation workflows.

---

## Career / Portfolio Value

This project demonstrates practical work across:

1. AI runtime systems

2. anomaly detection workflows

3. FastAPI backend engineering

4. observability architecture

5. Docker-based deployment

6. CI/CD validation

7. investigation-oriented system design


Built as part of an Applied AI Engineering project.

--- 