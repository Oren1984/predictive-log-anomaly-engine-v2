# Project Specification
## Predictive Log Anomaly Engine — OOP AI Pipeline

**Document Type:** Project Specification
**Assembled from:**
- `PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md` — Full document (Sections 1-6)
- `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md` — Sections 1, 2, 3

The original source documents remain unchanged. This file consolidates the project requirements and current repository state into one reference.

---

## Part A: Project Requirements
*Source: PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md*

---

## Predictive Log Anomaly Engine

## AI-Driven Proactive Monitoring System (AIOps)

1. Project Objective

Development of an AI-driven proactive monitoring system (AIOps) designed for the early detection of Anomaly Detection patterns in System Logs.

The system aims to identify potential disruptions in their early stages before they escalate into critical service availability failures.

The system architecture is based on:

Real-time data processing

Sequence Modeling

Hybrid learning models

These models combine:

Semantic text representation (NLP)

Deep Neural Networks

The system provides intelligent alerts classified by severity, implementing Object-Oriented Programming (OOP) principles to ensure modularity and scalability.



2. Problem Definition

Traditional Rule-based Monitoring tools focus on detecting symptoms of failures that have already occurred, such as:

Spikes in resource consumption (CPU / RAM)

Service crashes

This approach is inherently reactive, meaning alerts are only triggered after users are already experiencing degradation in service quality.

The primary challenge in using raw logs for proactive monitoring lies in:

Massive data volume

Informal and inconsistent structure

This project aims to bridge that gap by shifting the paradigm:

From symptom monitoring → to behavioral monitoring

The system learns the "language" and unique sequence of system events.

Instead of relying on fixed rules, the system autonomously learns the normal operating state and raises alerts when statistical or semantic deviations occur in real-time.

This enables:

Preventive maintenance

Early anomaly detection

Reduced system downtime


3. Development Path: Predictive Log Anomaly Engine

The system is built using a hybrid architecture combining:

NLP for log text processing

Deep Learning for sequence anomaly detection

# Step 1 — NLP Embedding

Converting raw logs into computational vectors via word representation models.

Models used:

Word2Vec

FastText

# Step 2 — Sequence Data Preparation

Preparing log sequences for deep neural networks.

Operations include:

Batch creation

Time-series windows

Tensor transformation using PyTorch

# Step 3 — Sequence Modeling

Learning system behavior over time based on the order of operations.

Models used:

LSTM

RNN

# Step 4 — Proactive Anomaly Detection Engine

Using Denoising Autoencoders.

The model learns to reconstruct healthy sequences of logs.

If reconstruction fails (high reconstruction error), the sequence is flagged as an anomaly.

# Step 5 — Severity Classification

A Multi-Layer Perceptron (MLP) classifier categorizes anomalies by severity.

Outputs include:

Info

Warning

Critical

# Step 6 — AIOps Infrastructure

Connecting the AI model to a real-time monitoring environment.

Technologies used:

Prometheus

Grafana


4. Project Architecture Overview
Phase	Objective	Technologies	OOP Implementation
NLP Embedding	Convert raw logs to vector space	Tokenization, Word2Vec, FastText	LogPreprocessor
Sequence Data Prep	Prepare time windows for neural networks	PyTorch Tensors, DataLoaders	LogDataset
Sequence Modeling	Learn behavior patterns over time	LSTM, RNN	SystemBehaviorModel
Anomaly Detection	Detect abnormal sequences	Denoising Autoencoders	AnomalyDetector
Severity Classification	Prioritize alerts	MLP, Adam Optimizer, Dropout	SeverityClassifier
AIOps Infrastructure	Deploy monitoring system	Prometheus, Grafana	ProactiveMonitorEngine


5. Detailed Technical Breakdown
# Stage 1: NLP Embedding

Logs arrive as raw text.

Machine learning models operate on numbers, so the first step is converting logs into continuous numerical vectors that preserve semantic meaning.

Text Cleaner

Removes irrelevant characters and normalizes variables.

Examples:

IP addresses → [IP]

Dates → [TIMESTAMP]

Convert text to lowercase

Tokenizer

Breaks each cleaned log entry into tokens (words or symbols).

Word2Vec

The core of the NLP stage.

Word2Vec learns contextual relationships between tokens.

Example:

Words appearing in similar contexts such as:

timeout
disconnect

will have vectors located close together in the vector space.

Aggregator

Performs Mean Pooling on all word vectors in a log line.

This produces a single vector representation for the entire log entry.

# Stage 2: Sequence Data Preparation

Proactive alerts rely on event sequences, not just single log entries.

Sliding Window Generator

Defines a fixed window size.

Example:

Window Size = 20 logs

Sequence creation:

Logs 1-20 → Window 1
Logs 2-21 → Window 2
Logs 3-22 → Window 3
PyTorch Dataset (OOP)

Custom class responsible for retrieving the i-th log window.

The window is converted into a Tensor:

[Sequence_Length, Vector_Size]
PyTorch DataLoader

Organizes windows into batches.

Example:

Batch Size = 32 windows

Shuffling ensures robust training.

Final Input Tensor

Final model input shape:

[Batch_Size, Sequence_Length, Vector_Size]

Example:
[32, 20, 100]
# Stage 3: Sequence Modeling (LSTM)

The objective is understanding the chronological evolution of events.

Unlike traditional models, LSTM maintains memory of previous events.

LSTM Layers

Processes sequences step-by-step while updating an internal Hidden State.

Example pattern:

Configuration Error
→ Network Latency
→ Service Timeout
Context Vector

After processing a sequence window, the LSTM produces a condensed vector representation summarizing the entire event sequence.

Output Projection

The final hidden state is passed through a Dense Layer to match the dimensions required by the anomaly detection engine.

# Stage 4: Anomaly Detection (Autoencoder)

This stage transforms the system from passive analysis to proactive detection.

The approach is self-supervised learning.

## Encoder

Compresses the context vector into a latent representation (bottleneck).

Only the most essential features of normal system behavior are preserved.

## Decoder

Attempts to reconstruct the original vector from the compressed representation.

## Reconstruction Error

If the input sequence represents normal behavior, reconstruction error is low.

If the sequence is anomalous, reconstruction quality deteriorates, producing high reconstruction error.

## Anomaly Flag

If reconstruction error exceeds a predefined threshold:

Anomaly Detected

The system raises a red flag before the actual crash occurs.

# Step 5: Severity Classification (MLP)

To prevent alert fatigue, anomalies are categorized by severity.

Classes include:

Info

Warning

Critical

Input Features

The classifier uses:

Latent vector from the Autoencoder

Reconstruction error score

Hidden Layers + Dropout

The MLP network processes these features.

Dropout helps prevent overfitting.

Softmax Output

The final layer applies Softmax, producing class probabilities.

Example output:

Critical: 80%
Warning: 15%
Info: 5%
# Step 6: AIOps Infrastructure

This stage connects the AI system to real production monitoring environments.

Live Log Stream

Logs are streamed from sources such as:

Kafka

Logstash

Direct file tailing

Metrics Exporter

Model outputs are converted into HTTP metrics readable by monitoring tools.

Prometheus & Grafana

Prometheus collects the metrics.

Grafana visualizes:

Reconstruction Error

Anomaly counts

System behavior trends

Alert Manager

Triggers notifications when critical anomalies persist.

Example integrations:

Slack

Email

Incident systems

---

## Part B: Repository Gap Analysis — Executive Summary and Current State
*Source: REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md — Sections 1, 2, 3*

---

# Repository Gap Analysis: OOP AI Pipeline Refactor
## Predictive Log Anomaly Engine

**Document Version:** 1.0
**Analysis Date:** 2026-03-06
**Source Requirements:** `PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md`
**Analyst:** Claude Code (Automated Repository Review)

---

## 1. Executive Summary

### What the New Requirements Document Asks For

`PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md` defines a six-stage AI pipeline for proactive AIOps log anomaly detection. The document prescribes a specific set of named classes, a specific ML architecture, and a production-grade monitoring integration. The six stages and their prescribed classes are:

1. **NLP Embedding** — `LogPreprocessor` class (Word2Vec / FastText semantic embeddings)
2. **Sequence Data Prep** — `LogDataset` class inheriting `torch.utils.data.Dataset` (PyTorch DataLoaders, 3D tensors)
3. **Sequence Modeling** — `SystemBehaviorModel` class (LSTM / RNN / Attention)
4. **Anomaly Detection** — `AnomalyDetector` class (Denoising Autoencoder, reconstruction error)
5. **Severity Classification** — `SeverityClassifier` class (MLP with Softmax, three levels: Info / Warning / Critical)
6. **AIOps Infrastructure** — `ProactiveMonitorEngine` class (Prometheus, Grafana, live log stream)

The document further requires Python-only implementation, strict OOP class boundaries, a clean `main.py` entrypoint, and readiness for a future UI layer.

### Current State of the Repository

The repository is a mature, multi-stage engineering project built iteratively across eight documented stages. It has a FastAPI REST API, Prometheus/Grafana observability stack, Docker + CI/CD pipeline, 233 automated tests, and two ML models (IsolationForest baseline + causal Transformer). The code is substantially object-oriented, with 15+ source classes across 12 packages.

However, the current ML architecture diverges significantly from the requirements:

- **NLP Embedding**: Uses regex-based template mining and integer token IDs, not Word2Vec/FastText semantic vectors.
- **Sequence Modeling**: Uses a causal GPT-style Transformer (next-token prediction), not an LSTM/RNN.
- **Anomaly Detection**: Uses IsolationForest (scikit-learn), not a Denoising Autoencoder.
- **Severity Classification**: Uses a hard-coded score/threshold ratio rule, not an MLP classifier.
- **Class Names**: The required class names (`LogPreprocessor`, `LogDataset`, `SystemBehaviorModel`, `AnomalyDetector`, `SeverityClassifier`, `ProactiveMonitorEngine`) do not exist in the codebase.

### Overall Alignment Level

| Dimension | Alignment |
|---|---|
| Python-only implementation | **Full** |
| OOP architectural intent | **Moderate** |
| Required class names | **None** |
| NLP embedding approach | **None** (different technique) |
| Sequence data preparation | **Partial** (no PyTorch DataLoader) |
| Sequence modeling (LSTM) | **None** (Transformer instead) |
| Anomaly detection (Autoencoder) | **None** (IsolationForest instead) |
| Severity classification (MLP) | **None** (rule-based instead) |
| AIOps infrastructure (Prometheus/Grafana) | **Full** |
| Alert management | **Full** |
| Docker/CI/CD readiness | **Full** |
| Test coverage | **Good** (233 tests) |

**Summary**: The infrastructure layer (API, monitoring, Docker, CI) is well-aligned. The ML/AI pipeline layer is architecturally incompatible with the requirements and would require a complete replacement of the learning components.

---

## 2. What the New Requirements Document Actually Defines

### Architecture Overview

The requirements document (`PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md`) defines a **hybrid deep learning pipeline** combining NLP semantics with sequential behavioral modeling. It is not a simple template-matching or isolation-based system; it is a self-supervised deep learning architecture.

### Intended Pipeline and Design Philosophy

The pipeline follows a cascaded encoder-classifier pattern:

```
Raw Log Text
    |
    v  [Stage 1: LogPreprocessor]
Word2Vec/FastText Vectors (e.g., [100-dim vector per log line])
    |
    v  [Stage 2: LogDataset + DataLoader]
3D Tensor: [Batch_Size=32, Sequence_Length=20, Vector_Size=100]
    |
    v  [Stage 3: SystemBehaviorModel (LSTM)]
Context Vector (condensed behavioral "summary" of the window)
    |
    v  [Stage 4: AnomalyDetector (Denoising Autoencoder)]
Reconstruction Error (low = normal, high = anomaly)
    |
    v  [Stage 5: SeverityClassifier (MLP)]
Severity Probabilities: [Info%, Warning%, Critical%]
    |
    v  [Stage 6: ProactiveMonitorEngine]
Prometheus Metrics + Grafana Dashboard + Alert Notifications
```

### OOP Expectations

The document explicitly names six classes. Each class is responsible for exactly one stage:

| Stage | Class | Superclass / Framework |
|---|---|---|
| 1 | `LogPreprocessor` | None specified |
| 2 | `LogDataset` | `torch.utils.data.Dataset` |
| 3 | `SystemBehaviorModel` | Implicit: `nn.Module` |
| 4 | `AnomalyDetector` | Implicit: `nn.Module` |
| 5 | `SeverityClassifier` | Implicit: `nn.Module` |
| 6 | `ProactiveMonitorEngine` | None specified |

The document states "Object-Oriented Programming (OOP) principles to ensure modularity and scalability" as an explicit design goal.

### Role of main/UI

The document implies a main execution entrypoint that instantiates and connects the six classes. The `ProactiveMonitorEngine` is the top-level orchestrator that connects the AI engine to production systems.

---

## 3. Current Repository Assessment

### Repository Structure

```
predictive-log-anomaly-engine/
|-- src/                          # Main application source code
|   |-- api/                      # FastAPI app, routes, schemas, settings, UI
|   |-- alerts/                   # AlertManager, Alert, AlertPolicy, N8nClient
|   |-- data/                     # Synthetic data generators (legacy + active)
|   |-- data_layer/               # LogEvent model, data loader
|   |-- health/                   # HealthChecker
|   |-- modeling/
|   |   |-- baseline/             # IsolationForest model, feature extractor, calibrator
|   |   |-- transformer/          # GPT-style Transformer, config, trainer, scorer
|   |-- observability/            # MetricsRegistry, MetricsMiddleware, logging
|   |-- parsing/                  # RegexLogParser, JsonLogParser, EventTokenizer
|   |-- runtime/                  # InferenceEngine, SequenceBuffer, RiskResult
|   |-- security/                 # AuthMiddleware (API key)
|   |-- sequencing/               # SlidingWindowSequenceBuilder, SessionSequenceBuilder
|   |-- synthetic/                # Generator, patterns, scenario_builder
|   |-- app/                      # (empty __init__ placeholder)
|   |-- core/contracts/           # (empty __init__ placeholder)
|
|-- ai_workspace/                 # Exploratory scripts (stages 21-26)
|   |-- stage_21_sampling/        # Sampling script
|   |-- stage_22_template_mining/ # Template mining
|   |-- stage_23_sequence_builder/# Feature matrix builders
|   |-- stage_24_baseline_model/  # IsolationForest training scripts
|   |-- stage_25_evaluation/      # Evaluation scripts
|   |-- stage_26_hdfs_supervised/ # Supervised HDFS model
|   |-- reports/, logs/, prompts/,
|       monitoring/, docker/,
|       system_audit/, system_design/, ...
|
|-- scripts/                      # CLI runner scripts (stages 01-08)
|-- tests/                        # 233 tests (unit + integration)
|-- data/
|   |-- raw/                      # HDFS.log, BGL.log source data
|   |-- processed/                # events_unified.csv (15.9M rows)
|   |-- intermediate/             # templates, sequences, features
|   |-- models/                   # isolation_forest*.pkl, hdfs_supervised*.pkl
|
|-- models/                       # Runtime model artifacts (baseline.pkl, transformer.pt)
|-- artifacts/                    # vocab.json, templates.json, threshold*.json
|-- templates/                    # index.html (demo UI)
|-- prometheus/                   # prometheus.yml
|-- grafana/                      # Provisioning configs, dashboards JSON
|-- docker-compose.yml
|-- Dockerfile
|-- requirements.txt
|-- pyproject.toml
|-- .github/workflows/ci.yml
```

### Existing Architecture

The codebase is organized around eight development stages:

- **Stages 1-4 (Data + Modeling)**: Data loading, parsing, template mining, sequence building, baseline (IsolationForest) and transformer model training. Most exploratory work lives in `ai_workspace/`.
- **Stage 5 (Runtime)**: `InferenceEngine` + `SequenceBuffer` — core streaming inference classes in `src/runtime/`.
- **Stage 6 (Alerts)**: `AlertManager` + `AlertPolicy` + `Alert` — alert lifecycle with deduplication and cooldown in `src/alerts/`.
- **Stage 7 (API)**: FastAPI application factory (`create_app`), pipeline container, auth middleware, Prometheus metrics, demo UI in `src/api/`.
- **Stage 8 (DevOps)**: Docker Compose, CI workflow (pytest + trivy + docker smoke test), Grafana dashboards.

### Current Runtime Flow

```
POST /ingest -> Pipeline.process_event()
    -> InferenceEngine.ingest(event)
        -> SequenceBuffer.ingest() [accumulate tokens by service key]
        -> if stride boundary: score window
            -> BaselineFeatureExtractor.transform() [template frequency features]
            -> BaselineAnomalyModel.score() [IsolationForest negated score]
            OR
            -> AnomalyScorer.score() [Transformer NLL per token]
        -> RiskResult (stream_key, risk_score, is_anomaly, threshold, evidence)
    -> AlertManager.emit(risk_result)
        -> AlertPolicy.should_alert() + classify_severity() [score/threshold ratio]
        -> Alert (alert_id, severity, service, score, evidence)
    -> return {window_emitted, risk_result, alert}
```

### Existing Monitoring and Infrastructure Components

- `MetricsRegistry`: Prometheus counters and histograms (`ingest_events_total`, `alerts_total`, `ingest_latency_seconds`, etc.)
- `MetricsMiddleware`: HTTP middleware recording request latency
- Grafana dashboard: `stage08_api_observability.json` (5 panels)
- Prometheus scrape config: `prometheus/prometheus.yml`
- Docker Compose: `api:8000`, `prometheus:9090`, `grafana:3000`
