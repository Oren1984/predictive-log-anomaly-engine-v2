## Original System Design Ticket

# Project Vision
The goal of the project is to build a proactive AI system that learns the "language of failures" in software systems.

Instead of reacting to failures after they happen, the system analyzes sequences of system events and detects toxic behavioral patterns that indicate an upcoming failure.

The system raises alerts before critical failures impact end users.

The project focuses on building a real system pipeline rather than a notebook demonstration.


## High-Level Architecture

The system is designed as a multi‑layer pipeline:

1. Data Strategy and Contracts

2. Preprocessing and Template Mining

3. Sequence Modeling (AI Core)

4. Runtime Inference Engine

5. Alerts and Integrations

6. API Layer

7. Observability

8. Docker and CI/CD Automation


## Stage 0 – Dataset Strategy

The project may start with one of several datasets:

# Option A – Log Data for Anomaly Detection (Recommended)

A combined dataset containing multiple anomaly‑detection log datasets.

Advantages:

- Quick start

- Contains several environments

- Suitable for sequence modeling

# Option B – BGL (Blue Gene/L)

A well‑known dataset used in research for log anomaly detection.

Advantages:

- Academic credibility

- Realistic failure patterns

- Easy to explain in demos

# Option C – Synthetic Logging Dataset

Used for rapid prototyping and demonstrations.

Advantages:

- Quick MVP

- Controlled failure patterns


## Stage 1 – Data Layer

Goal: unify all data sources into a consistent schema.

Core classes:

- KaggleDatasetLoader

- LogEvent (dataclass)

- SyntheticLogGenerator

- FailurePattern abstraction


Example failure patterns:

- MemoryLeakPattern

- DiskFullPattern

- AuthBruteForcePattern

- NetworkFlapPattern

Synthetic scenarios simulate the following flow:

normal → degradation → failure

Deliverables:

- data/raw

- data/synth

- data/processed/events.parquet

- schema.md


## Stage 2 – Parsing and Template Mining

Goal: transform raw logs into stable templates and tokens.

Core components:

- LogParser interface

- JsonLogParser

- RegexLogParser

- TemplateMiner

- EventTokenizer

Deliverables:

- artifacts/templates.json

- artifacts/vocab.json

- processed/events_tokenized.parquet


## Stage 3 – Sequence Builder

Goal: convert tokenized logs into sequences suitable for modeling.

Core classes:

- Sequence (dataclass)

- SlidingWindowSequenceBuilder

- SessionSequenceBuilder

- DatasetSplitter

Typical parameters:

window size: 50 events stride: 10

Deliverables:

- processed/sequences_train.parquet

- processed/sequences_val.parquet

- processed/sequences_test.parquet


## Stage 4 – Modeling
### Baseline Model (Required)

Before introducing complex models, a stable baseline anomaly model is implemented.

Components:

- BaselineFeatureExtractor

- BaselineAnomalyModel

- ThresholdCalibrator

Outputs:

- anomaly score per sequence

- calibrated threshold

Deliverables:

- models/baseline.pkl

- artifacts/threshold.json

- reports/metrics.json

### Optional Upgrade – Transformer Model

A transformer model may be trained for Next‑Token Prediction.

Components:

- TransformerConfig

- NextTokenTransformerModel

- Trainer

- AnomalyScorer

The transformer predicts the probability of the next log event.

If the predicted event is associated with failure patterns, the system raises a risk signal.


## Stage 5 – Runtime Inference

Goal: evaluate logs in real time.

Core components:

- SequenceBuffer

- InferenceEngine

- RiskResult dataclass

Flow:

log event → buffer update → sequence scoring → threshold comparison → risk output


## Stage 6 – Alerts and n8n Integration

Goal: trigger real alerts.

Core classes:

- Alert

- AlertPolicy

- AlertManager

- N8nWebhookClient

Example alert flow:

RiskResult → AlertPolicy → AlertManager → Webhook

Possible integrations:

- Slack

- Email

- GitHub Issues


## Stage 7 – API, Security and Observability

API implemented using FastAPI.

Endpoints:

- POST /ingest

- GET /alerts

- GET /health

- GET /metrics

Security features:

- API key or JWT protection

- request validation

Observability:

- Prometheus metrics

- health checks

- Grafana dashboards


## Stage 8 – DevOps and CI/CD

Goal: make the system reproducible and always runnable.

Components:

- Docker

- docker-compose

- API container

- optional monitoring stack

### CI/CD

- GitHub Actions pipeline:

- lint

- pytest

- docker build

- integration smoke test

- security scanning