## Predictive Log Anomaly Engine

AI-powered observability and anomaly detection system for software logs.

The Predictive Log Anomaly Engine analyzes behavioral patterns in log streams and detects abnormal activity before full service failure occurs.

Instead of reacting only after incidents happen, the engine analyzes event sequences in real time, scores anomalous behavior, generates alerts, and exposes a complete observability stack for investigation.

---

## Tech Stack

Python • FastAPI • Docker • Prometheus • Grafana • PyTorch • Pytest • GitHub Actions

---

## Overview

Traditional monitoring systems usually detect failures after they already impact the system, for example through CPU spikes, crashes, or error bursts.

The Predictive Log Anomaly Engine takes a more proactive approach by analyzing log behavior patterns rather than simple metrics.

The system:

1. parses and normalizes raw logs

2. extracts behavioral templates

3. builds event sequences

4. generates semantic embeddings

5. applies AI-based anomaly detection

6. classifies severity levels

7. generates alerts and exposes observability dashboards

The result is a full AI runtime pipeline combined with an observability and investigation layer.

---

## Key Capabilities

1. Real-time log anomaly detection using behavioral    
   sequence analysis

2. Multi-stage AI inference pipeline

3. Severity scoring and alert generation

4. FastAPI service exposing ingestion and investigation  
   endpoints

5. Prometheus metrics and Grafana dashboards

6. Docker-based deployment

7. CI/CD validation with automated tests

8. Interactive demonstration notebooks

---

## System Architecture

The system follows a full AI runtime pipeline:

          Logs
            ↓
    Parsing & Template Mining
            ↓
      Sequence Builder
            ↓
    Embedding Generation (Word2Vec)
            ↓
      Behavior Modeling
            ↓
    Autoencoder Anomaly Detection
            ↓
      Severity Classification
            ↓
        Alert Manager
            ↓
      FastAPI Service
            ↓
      Prometheus + Grafana
            ↓
      Investigation UI

---

## Main Components
1. Parsing & Template Mining

  Transforms raw logs into structured templates that reduce noise while preserving behavioral patterns.

2. Sequence Builder

  Builds event windows and behavioral sequences that represent operational system activity.

3. Embedding Engine

  Uses Word2Vec embeddings to convert log templates into semantic vector representations.

4. Behavior Model

  Learns normal operational sequences using a deep learning behavioral model.

5. Autoencoder Anomaly Detector

  Detects abnormal patterns by measuring reconstruction error from learned normal behavior.

6. Severity Classifier

  Assigns severity levels to detected anomalies based on learned patterns and rule-based signals.

7. Alert Manager

  Generates alerts with severity levels and handles alert lifecycle management.

8. FastAPI Runtime Service

  Provides:

  - ingestion endpoints

  - system health signals

  - alert queries

  - investigation endpoints

  - UI serving

9. Observability Layer

The project integrates a full observability stack:

  - Prometheus metrics collection

  - Grafana dashboards

  - system health visibility

  - ingestion monitoring

  - alert activity monitoring

---

## Demo Notebooks

The repository includes interactive demonstration notebooks.

These notebooks serve as the primary explanation and visualization layer of the system.

notebooks/
predictive_log_anomaly_engine_demo.ipynb
predictive_log_anomaly_engine_gpu_demo.ipynb

The notebooks demonstrate:

- log ingestion simulation

- anomaly scoring visualization

- dynamic graphs of detection behavior

- GPU acceleration demonstration

---

## Demo Scripts

The repository also includes runnable demo scripts:

demo/
predictive_log_anomaly_engine_demo.py
predictive_log_anomaly_engine_gpu_demo.py

These scripts generate synthetic events and visualize anomaly detection behavior.

---

## Quick Start

Build and run the system:

docker compose -f docker\docker-compose.yml build
docker compose -f docker\docker-compose.yml up

---

## Open the Services

- API / UI
http://localhost:8000

- Prometheus
http://localhost:9090

- Grafana
http://localhost:3000

---

## Demo Walkthrough
Step	Action	Expected Result
1	Ingest events	Synthetic logs enter the runtime pipeline
2	Open alerts view	Alerts appear with severity and score
3	Open dashboards	Prometheus / Grafana show runtime metrics
4	Query investigation	System returns investigation information

---

## Evaluation (V1 vs V2)

The repository includes evaluation tooling for comparing the V1 and V2 anomaly pipelines.

### Prerequisites

All four model artifacts must exist:

models/embeddings/word2vec.model
models/behavior/behavior_model.pt
models/anomaly/anomaly_detector.pt
models/severity/severity_classifier.pt

Train them if missing:

python -m training.train_embeddings
python -m training.train_behavior_model
python -m training.train_autoencoder
python -m training.train_severity_model

### Run Evaluation
python scripts/evaluate_v2.py

Evaluates labeled HDFS sessions and generates performance comparison.

Output is written to:

evaluation_report.json

---

## Testing

Fast tests

pytest -m "not slow"

Integration tests

pytest -m integration

---

## Documentation Structure

Additional documentation is available under:

docs/

1. docs/current_system — architecture and roadmap

2. docs/api — API reference

3. docs/operations — deployment, alerts, metrics

4. docs/system_validation — validation reports

---

## Project Team

Developed as part of an Applied AI Engineering project.

- Oren Salami
  DevOps, QA, Architecture Design, Technical Specification

- Dan Kalfon
  Backend Engineering, Architecture Design, Technical Specification

- Nahshon Raizman
  Frontend Development, UI Design, Architecture Design, Technical Specification

- Jonathan Finkelstein
  Frontend Development, UI Design, Architecture Design, Technical Specification

---

## Project Status

Current repository status:

1. runtime inference pipeline implemented

2. anomaly detection models integrated

3. alert pipeline implemented

4. observability stack integrated

5. Grafana and Prometheus configured

6. Docker deployment implemented

7. evaluation framework implemented

8. investigation UI implemented

All tests passing (578 tests) and full containerized runtime included.

---

## Career / Portfolio Value

This project demonstrates practical work across:

1. AI runtime systems

2. anomaly detection pipelines

3. FastAPI backend engineering

4. observability architecture

5. Docker-based deployment

6. CI/CD validation

7. investigation-oriented system design

Built as part of an Applied AI Engineering project.