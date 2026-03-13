# Master Architecture and Execution Plan
## Predictive Log Anomaly Engine — OOP AI Pipeline

**Document Type:** Consolidated Master Reference
**Version:** 1.0
**Date:** 2026-03-08
**Status:** Active — Authoritative Reference

---

## Document Purpose

This document is a consolidated master reference created from four original planning and specification documents:

1. `IMPLEMENTATION_ACTION_PLAN.md` — Phase-by-phase engineering roadmap
2. `PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md` — System requirements and OOP architecture contract
3. `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md` — Current repository state, gap identification, and alignment assessment
4. `UI_OBSERVABILITY_INVESTIGATION_CENTER.md` — UI layer specification, required API endpoints, and panel design

All four original documents remain unchanged and authoritative in their own right. This consolidated document merges their content into a single coherent reference for implementation. Where documents overlap, the more specific detail is preserved. Where documents specify gaps, those gaps are reflected in the work plan. No content from the originals has been omitted or contradicted.

In addition to the four source documents, this plan incorporates five approved upgrade additions that were reviewed and confirmed as compatible with the current architecture scope. These additions are integrated at their correct positions in the roadmap.

---

## Table of Contents

1. [Document Purpose](#document-purpose)
2. [System Objective](#2-system-objective)
3. [Problem Definition](#3-problem-definition)
4. [Final Agreed System Scope](#4-final-agreed-system-scope)
5. [Final Agreed AI Pipeline](#5-final-agreed-ai-pipeline)
6. [Final Agreed OOP Architecture](#6-final-agreed-oop-architecture)
7. [Repository Gap Summary](#7-repository-gap-summary)
8. [Final Agreed UI Observability Architecture](#8-final-agreed-ui-observability-architecture)
9. [Approved Upgrade Additions](#9-approved-upgrade-additions)
10. [Experimental and Optional Components](#10-experimental-and-optional-components)
11. [Deferred Items](#11-deferred-items)
12. [Architecture Constraints and Non-Negotiables](#12-architecture-constraints-and-non-negotiables)
13. [Consolidated Implementation Roadmap](#13-consolidated-implementation-roadmap)
14. [Final Recommendation](#14-final-recommendation)

---

## 2. System Objective

The Predictive Log Anomaly Engine is an AI-driven proactive monitoring system for the early detection of anomaly patterns in system logs, designed to identify potential disruptions before they escalate into critical service availability failures.

The system shifts the operational paradigm from symptom monitoring to behavioral monitoring. Instead of relying on fixed rules that trigger after a failure has already occurred, the system learns the normal operating state of a service autonomously and raises alerts when statistical or semantic deviations are detected in real time. This enables preventive maintenance, early anomaly detection, and reduced system downtime.

The architecture combines three foundational capabilities:

- **Real-time data processing**: log events are ingested and processed as a continuous stream
- **Sequence modeling**: temporal behavioral patterns are learned over sliding windows of log events
- **Hybrid learning models**: semantic NLP representations and deep neural networks are combined into a cascaded detection pipeline

The system produces intelligent alerts classified by severity, implemented using Object-Oriented Programming (OOP) principles to ensure modularity, testability, and scalability.

---

## 3. Problem Definition

Traditional rule-based monitoring tools focus on detecting symptoms of failures that have already occurred — resource spikes, service crashes, threshold breaches. This approach is inherently reactive. Alerts are triggered after users are already experiencing degradation in service quality.

The primary challenge in using raw logs for proactive monitoring is threefold:

- **Massive data volume**: production systems generate millions of log events per day
- **Informal and inconsistent structure**: log formats vary by service, version, and context
- **Event sequence dependency**: individual log lines are often meaningless in isolation; anomalies are detectable only from the order and composition of event sequences

The Predictive Log Anomaly Engine addresses these challenges by learning the "language" and unique temporal sequencing of normal system events. Anomalies are flagged not because a rule has been violated, but because the system's behavioral signature deviates from what the model learned as its normal reconstruction pattern.

The AI pipeline is structured to handle both the HDFS and BGL log datasets:

- **HDFS** (Hadoop Distributed File System): high volume (10.9 million normal events, 288,250 anomalous), structured block-level operations, approximately 41 templates
- **BGL** (Blue Gene/L supercomputer): 348,460 normal events, 4.4 million anomalous (27.63% of total), richer template vocabulary (7,792 unique templates), more variable token patterns

---

## 4. Final Agreed System Scope

### What This System Is

- An AI-driven proactive log anomaly detection engine
- A production-grade FastAPI REST service with Prometheus and Grafana observability
- A six-stage deep learning pipeline: NLP embedding -> sequence preparation -> LSTM behavior modeling -> Denoising Autoencoder anomaly detection -> MLP severity classification -> AIOps monitoring integration
- A read-only observability and investigation UI (Observability + AI Investigation Center)
- A containerized deployment using Docker Compose

### What This System Is Not

- A replacement for Grafana infrastructure metrics (both coexist and serve different purposes)
- A Kafka consumer or log shipper (HTTP POST ingestion is the current interface; streaming adapters are deferred)
- A Kubernetes-based deployment (Docker Compose is the target environment)
- An admin control panel (the UI is strictly read-only and observational)
- A Doc2Vec or Transformer-as-primary-model system (LSTM is the main sequence model; Transformer remains only as a fallback)

### What Stays Unchanged Throughout the Refactor

The following components are complete, tested, and must not be modified during the AI pipeline refactor:

| Component | Location | Reason |
|---|---|---|
| FastAPI application factory | `src/api/app.py` | 233 tests depend on it |
| API routes and schemas | `src/api/routes.py`, `src/api/schemas.py` | REST contract is stable |
| Settings / configuration | `src/api/settings.py` | Env-driven config is complete |
| AuthMiddleware | `src/security/auth.py` | API key auth is correct and tested |
| AlertManager | `src/alerts/manager.py` | Deduplication and cooldown logic is complete |
| Alert + AlertPolicy models | `src/alerts/models.py` | Severity bucket model is reusable |
| N8nWebhookClient | `src/alerts/n8n_client.py` | Outbox pattern is correct |
| MetricsRegistry + MetricsMiddleware | `src/observability/metrics.py` | Prometheus counters and histograms are correct |
| HealthChecker | `src/health/checks.py` | Works correctly |
| Prometheus config | `prometheus/prometheus.yml` | No changes needed |
| Grafana dashboard | `grafana/dashboards/` | Extend with new panels only |
| Dockerfile | `Dockerfile` | Works; update only if new system packages are needed |
| Docker Compose | `docker-compose.yml` | No changes during the AI refactor |
| CI/CD workflow | `.github/workflows/ci.yml` | No changes during the AI refactor |
| RegexLogParser / JsonLogParser | `src/parsing/parsers.py` | First-pass log structuring; feeds LogPreprocessor |
| EventTokenizer | `src/parsing/tokenizer.py` | Used by the `explain()` method in InferenceEngine |
| SequenceBuffer | `src/runtime/sequence_buffer.py` | Streaming buffer logic is correct; rewire to new model |
| RiskResult | `src/runtime/types.py` | Clean data class; keep as-is |
| All existing tests | `tests/` | 233 tests must pass throughout the entire refactor |

---

## 5. Final Agreed AI Pipeline

The agreed pipeline is a cascaded six-stage architecture. Each stage has exactly one responsible class. Data flows in one direction from raw log text to severity-classified alert.

```
Raw Log Line (text)
    |
    v  [Stage 1: LogPreprocessor]
    Text cleaning + Word2Vec embedding -> Float vector [vec_dim=100]
    |
    v  [Stage 2: LogDataset + DataLoader]
    Sliding window assembly -> 3D Tensor [Batch=32, Seq=20, Vec=100]
    |
    v  [Stage 3: SystemBehaviorModel (LSTM)]
    Temporal sequence encoding -> Context Vector [hidden_dim]
    |
    v  [Stage 4: AnomalyDetector (Denoising Autoencoder)]
    Reconstruction error (float) + Latent vector [latent_dim]
    |
    v  [Stage 5: SeverityClassifier (MLP + Softmax)]
    Severity probabilities -> Info% | Warning% | Critical%
    |
    v  [Stage 6: ProactiveMonitorEngine]
    |         |                    |
    v         v                    v
RiskResult  AlertManager      MetricsRegistry
    |         |    |               |
    |         v    v               v
    |      Alert  Ring          Prometheus
    |      fired  buffer        /metrics
    |             |
    v             v
POST /ingest   GET /alerts
response       GET /ws/alerts (push)
               GET /score/history
               GET /pipeline/status
```

### Stage 1 — NLP Embedding (LogPreprocessor)

**Objective**: Convert raw log text into fixed-size float vectors that preserve semantic meaning.

**Process**:
1. Text cleaner: lowercase conversion; normalize IP addresses to `[IP]`, timestamps to `[TIMESTAMP]`, block IDs to `[BLK]`, node identifiers to `[NODE]`, file paths to `[PATH]`, hex values to `[HEX]`, numeric tokens to `[NUM]`
2. Tokenizer: word-level split of the cleaned text
3. Word2Vec: training on the log corpus; words in similar contexts (e.g., `timeout`, `disconnect`) produce nearby vectors
4. Aggregator: mean pooling across all word vectors in a log line produces a single fixed-size vector per log entry

**Input**: Raw log message string (the `message` field of `LogEvent`)
**Output**: `numpy.ndarray` of shape `[vec_dim]` — one 100-dimensional float vector per log line
**Artifact**: `models/word2vec.model`

**Existing assets that help**: `src/parsing/template_miner.py:TemplateMiner._SUBS` — nine regex substitutions that partially implement the normalization requirement; these patterns are the starting point for `LogPreprocessor.clean()`.

---

### Stage 2 — Sequence Data Preparation (LogDataset)

**Objective**: Wrap embedded log sequences into a PyTorch-compatible dataset that yields sliding window tensors.

**Process**:
1. Sliding window generator: defines a fixed window size (e.g., 20 logs) and stride; generates overlapping windows
2. PyTorch Dataset: custom class inheriting `torch.utils.data.Dataset`; `__getitem__(idx)` returns `(FloatTensor[seq_len, vec_dim], label)`
3. DataLoader: organizes windows into batches; shuffles for training

**Input**: List of log embedding arrays and labels; window size and stride parameters
**Output per `__getitem__`**: `(torch.FloatTensor[seq_len, vec_dim], label)`
**DataLoader batch shape**: `[batch_size=32, seq_len=20, vec_dim=100]`
**Artifact**: `data/intermediate/log_embeddings.npy` (saved embedding cache)

**Existing assets that help**: `src/sequencing/builders.py:SlidingWindowSequenceBuilder` — sliding window logic over a sequence list; the window and stride parameters can be adapted directly.

---

### Stage 3 — Sequence Modeling (SystemBehaviorModel — LSTM)

**Objective**: Learn temporal behavioral patterns in log sequences. Produce a context vector summarizing the behavioral signature of a window.

**Process**:
1. LSTM layers process the 3D input tensor step by step, updating an internal hidden state
2. The final hidden state is the context vector — a condensed behavioral summary of the entire window
3. An optional dense projection layer reshapes the context vector for Autoencoder input

**Input**: `torch.FloatTensor` of shape `[batch_size, seq_len, vec_dim]`
**Output**: Context Vector `torch.FloatTensor` of shape `[batch_size, hidden_dim]`
**Config**: `LSTMConfig` dataclass — `input_dim`, `hidden_dim`, `num_layers`, `dropout`, `learning_rate`, `max_epochs`, `patience`
**Artifact**: `models/behavior_model.pt`

**Existing assets that help**: `src/modeling/transformer/model.py:NextTokenTransformerModel` — provides the `save()` / `load()` / `forward()` pattern to mirror; `src/modeling/transformer/trainer.py:Trainer` — training loop structure (AdamW, CosineAnnealingLR, early stopping) to adapt.

---

### Stage 4 — Anomaly Detection (AnomalyDetector — Denoising Autoencoder)

**Objective**: Self-supervised detection of anomalous log sequences via reconstruction error. Trained exclusively on normal sequences.

**Process**:
1. Encoder: compresses context vector into a bottleneck latent representation — only the most essential features of normal behavior are preserved
2. Decoder: attempts to reconstruct the original context vector from the latent representation
3. Reconstruction error: MSE between original context vector and its reconstruction — low for normal sequences, high for anomalous sequences
4. Threshold calibration: 95th percentile of reconstruction errors on a held-out normal validation set

**Input**: Context Vector `torch.FloatTensor[batch_size, hidden_dim]`
**Output**: `(reconstruction_error: float, latent_vector: FloatTensor[latent_dim])`
**Anomaly flag**: reconstruction_error exceeds calibrated threshold
**Artifacts**: `models/anomaly_detector.pt`, `artifacts/threshold_autoencoder.json`

**Existing assets that help**: `src/modeling/baseline/calibrator.py` — threshold calibration approach; `src/modeling/baseline/model.py:BaselineAnomalyModel` — fit/score/predict/save/load interface to mirror; `src/runtime/types.py:RiskResult` — `risk_score` field receives reconstruction error.

---

### Stage 5 — Severity Classification (SeverityClassifier — MLP)

**Objective**: Classify detected anomalies by severity to prevent alert fatigue.

**Process**:
1. Input features: latent vector from AnomalyDetector concatenated with reconstruction error scalar = `[latent_dim + 1]`
2. MLP architecture: `Linear -> ReLU -> Dropout -> Linear -> ReLU -> Dropout -> Linear -> Softmax`
3. Softmax output: three-class probability distribution — Info%, Warning%, Critical%
4. Training labels: generated from the existing `AlertPolicy.classify_severity()` ratio rule applied to reconstruction errors — a known approximation, documented, improvable later with human review

**Input**: `FloatTensor[latent_dim + 1]` (latent vector + reconstruction error)
**Output**: `FloatTensor[3]` — probabilities for `[Info, Warning, Critical]`
**Artifact**: `models/severity_classifier.pt`

**Existing assets that help**: `src/alerts/models.py:AlertPolicy.classify_severity()` — ratio thresholds (critical >= 1.5x, high >= 1.2x, medium >= 1.0x) provide the auto-labeling heuristic; after training, the MLP result replaces this rule's output.

---

### Stage 6 — AIOps Infrastructure (ProactiveMonitorEngine)

**Objective**: Top-level orchestrator that connects all six pipeline stages to the production monitoring environment.

**Role**: Replaces the current `Pipeline` container as the authoritative runtime coordinator. Absorbs `Pipeline.process_event()` and `load_models()` responsibilities and adds the new model chain.

**Input**: Log stream events (from HTTP POST, file tail, or future Kafka adapter)
**Output**: Risk scores, severity-classified alerts, Prometheus metrics

**Key methods**:
- `load_models()`: load all artifacts for all six pipeline stages
- `process_event(event: dict) -> dict`: run the full pipeline end to end
- `recent_alerts() -> list[dict]`: delegate to alert ring buffer
- `metrics_snapshot() -> dict`: return current pipeline component states and metric values

**Artifact**: No model artifact; this class is pure orchestration
**Location**: `src/engine/proactive_engine.py`

**Existing assets that help**: `src/api/pipeline.py:Pipeline` — direct predecessor; the current `process_event()` and `load_models()` methods are the templates; `src/observability/metrics.py:MetricsRegistry` — inject into constructor; record new metrics (`reconstruction_error_histogram`, `severity_info_total`, `severity_warning_total`, `severity_critical_total`).

---

## 6. Final Agreed OOP Architecture

### Six Required Classes

The requirements document defines a contract of exactly six named classes, one per pipeline stage. All six must be importable and available by the end of the refactor.

| Stage | Class | Location | Superclass | Status |
|---|---|---|---|---|
| 1 — NLP Embedding | `LogPreprocessor` | `src/preprocessing/log_preprocessor.py` | None | Does not exist — must be built |
| 2 — Sequence Data | `LogDataset` | `src/dataset/log_dataset.py` | `torch.utils.data.Dataset` | Does not exist — must be built |
| 3 — Behavior Model | `SystemBehaviorModel` | `src/modeling/behavior_model.py` | `nn.Module` (implicit) | Does not exist — must be built |
| 4 — Anomaly Detector | `AnomalyDetector` | `src/modeling/anomaly_detector.py` | `nn.Module` (implicit) | Does not exist — must be built |
| 5 — Severity Classifier | `SeverityClassifier` | `src/modeling/severity_classifier.py` | `nn.Module` (implicit) | Does not exist — must be built |
| 6 — AIOps Engine | `ProactiveMonitorEngine` | `src/engine/proactive_engine.py` | None | Does not exist — must be built |

### Target Folder Structure

```
predictive-log-anomaly-engine/
|
|-- src/
|   |-- preprocessing/
|   |   |-- __init__.py
|   |   |-- log_preprocessor.py       # Stage 1: LogPreprocessor
|   |
|   |-- dataset/
|   |   |-- __init__.py
|   |   |-- log_dataset.py            # Stage 2: LogDataset(Dataset)
|   |
|   |-- modeling/
|   |   |-- __init__.py
|   |   |-- behavior_model.py         # Stage 3: SystemBehaviorModel (LSTM)
|   |   |-- anomaly_detector.py       # Stage 4: AnomalyDetector (Autoencoder)
|   |   |-- severity_classifier.py    # Stage 5: SeverityClassifier (MLP)
|   |   |-- baseline/                 # Keep: IsolationForest (fallback)
|   |   |-- transformer/              # Keep: Transformer (fallback)
|   |
|   |-- engine/
|   |   |-- __init__.py
|   |   |-- proactive_engine.py       # Stage 6: ProactiveMonitorEngine
|   |
|   |-- runtime/
|   |   |-- inference_engine.py       # Keep; rewire to new models
|   |   |-- sequence_buffer.py        # Keep as-is
|   |   |-- types.py                  # Keep as-is
|   |
|   |-- api/
|   |   |-- app.py                    # Keep as-is
|   |   |-- routes.py                 # Keep; add four new endpoints
|   |   |-- schemas.py                # Keep; add new response schemas
|   |   |-- settings.py               # Keep; add MODEL_MODE=autoencoder
|   |   |-- pipeline.py               # Rewire to ProactiveMonitorEngine
|   |   |-- ui.py                     # Keep; upgrade RAG backend
|   |
|   |-- ui/
|   |   |-- __init__.py
|   |   |-- dashboard.py              # Streamlit dashboard (Phase 8)
|   |   |-- api_client.py             # Typed httpx wrapper
|   |   |-- components/
|   |   |   |-- status.py             # Panel 1: System Status
|   |   |   |-- alert_feed.py         # Panel 2: Live Alert Feed
|   |   |   |-- timeline.py           # Panel 3: Score Timeline
|   |   |   |-- pipeline.py           # Panel 4: Pipeline Status
|   |   |   |-- rag.py                # Panel 5: RAG Investigation
|   |   |-- README.md
|   |
|   |-- alerts/                       # Keep as-is
|   |-- observability/                # Keep; add new metrics
|   |-- parsing/                      # Keep; extend normalization
|   |-- sequencing/                   # Keep for streaming runtime path
|   |-- synthetic/                    # Keep; consolidate src/data/ here
|   |-- security/                     # Keep as-is
|   |-- health/                       # Keep as-is
|   |-- data_layer/                   # Keep as-is
|
|-- main.py                           # NEW: single project entrypoint
|-- scripts/                          # Training CLI scripts
|-- tests/                            # Keep all 233 tests; add new ones
|-- models/                           # Artifact storage
|-- artifacts/                        # JSON artifacts
|-- data/                             # Raw, processed, intermediate
|-- templates/                        # HTML demo UI
|-- prometheus/, grafana/             # No changes
|-- Dockerfile, docker-compose.yml    # No changes during AI refactor
|-- requirements.txt                  # Add: gensim>=4.3.0
|-- pyproject.toml                    # No changes
```

### Classes That Exist and Must Be Refactored

Three existing components require targeted changes after the new AI classes are built. None require a full rewrite.

| Component | Current Location | Required Change | Difficulty |
|---|---|---|---|
| `Pipeline` container | `src/api/pipeline.py` | After Phases 2-6, `load_models()` must load the new AI classes; `process_event()` must route through the new chain | Medium |
| `InferenceEngine` | `src/runtime/inference_engine.py` | Add a new `autoencoder` scoring path; keep `baseline` and `transformer` paths as fallbacks | Medium |
| `AlertPolicy.classify_severity()` | `src/alerts/models.py` | After Phase 6, replace the ratio rule with a call to `SeverityClassifier.predict()` | Low |

---

## 7. Repository Gap Summary

This section consolidates the findings of `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md`. It summarizes what is currently missing, what is present but misaligned, and what is production-ready.

### Critical Gaps (Must Be Built from Scratch)

| Required Item | Current State | Impact |
|---|---|---|
| `LogPreprocessor` class | Does not exist anywhere in `src/` | Blocks all AI pipeline work |
| Word2Vec / FastText embeddings | Not referenced anywhere | Blocks Stage 1 |
| Mean pooling aggregation | Does not exist | Blocks Stage 1 |
| `LogDataset(torch.utils.data.Dataset)` | Does not exist; `SlidingWindowSequenceBuilder` is not a Dataset | Blocks Stage 2 |
| 3D tensor `[B, T, V]` input pipeline | Does not exist; current input is 2D `[B, T]` integers | Blocks Stage 2 |
| `torch.utils.data.DataLoader` usage | Does not exist; `_make_batches()` is a plain generator | Blocks Stage 2 |
| `SystemBehaviorModel` (LSTM) | Does not exist; `NextTokenTransformerModel` is a GPT-style Transformer, different purpose | Blocks Stage 3 |
| LSTM hidden state / context vector | Does not exist | Blocks Stage 3 |
| `AnomalyDetector` (Denoising Autoencoder) | Does not exist; `BaselineAnomalyModel` wraps IsolationForest, incompatible architecture | Blocks Stage 4 |
| Reconstruction error thresholding | Does not exist; current system uses IsolationForest anomaly scores | Blocks Stage 4 |
| Latent space / bottleneck | Does not exist | Blocks Stage 4 |
| `SeverityClassifier` (MLP + Softmax) | Does not exist; `AlertPolicy.classify_severity()` is a hard-coded ratio rule | Blocks Stage 5 |
| Severity-labeled training data | Does not exist; dataset has binary labels only (0=normal, 1=anomaly) | Blocks Stage 5 training |
| `ProactiveMonitorEngine` class | Does not exist by this name; functionality is split across `Pipeline`, `InferenceEngine`, `MetricsRegistry` | Blocks Stage 6 |
| `main.py` single entrypoint | Does not exist; entry points are scattered in `scripts/` | Structural gap |

### Partial Gaps (Exist in Different Form — Need Extension or Replacement)

| Required Item | Current State | Gap |
|---|---|---|
| Text cleaning / normalization | `TemplateMiner._SUBS` — 9 regex substitutions | Does not produce NLP-quality normalized text; focused on template deduplication, not semantic preservation |
| Word-level tokenization | `EventTokenizer` maps template_ids to integer token_ids | Entirely different paradigm; not word-level NLP tokenization |
| Sliding window sequencing | `SlidingWindowSequenceBuilder` — operates on integer token sequences | Incompatible with float vector embeddings |
| Three-class severity output | `AlertPolicy` uses four buckets: low, medium, high, critical | Naming and logic mismatch with Info/Warning/Critical MLP output |
| AIOps infrastructure class | Functionality distributed across `Pipeline`, `InferenceEngine`, `MetricsRegistry` | No single `ProactiveMonitorEngine` class |

### Missing API Endpoints (Required by UI)

| Endpoint | Status | Required By |
|---|---|---|
| `GET /pipeline/status` | Not implemented | UI Panel 4 — Pipeline Component Status |
| `GET /score/history` | Not implemented | UI Panel 3 — Score Timeline |
| `GET /alerts/{alert_id}` | Not implemented | UI Panel 5 — RAG Investigation |
| `GET /ws/alerts` | Not implemented | UI Panel 2 — Live Alert Feed (real-time push) |

### Production-Ready Components (No Changes Required)

| Component | Assessment |
|---|---|
| FastAPI application + all current endpoints | Fully functional; 233 tests pass |
| AuthMiddleware (X-API-Key) | Correct and tested |
| AlertManager (dedup + cooldown) | Correct and tested |
| MetricsRegistry + Prometheus scrape | Production-ready |
| Grafana dashboard (5 panels) | Production-ready; extend with new metrics |
| Docker Compose stack | Production-ready |
| CI/CD workflow | Passes with all current tests |
| Docker + CI/CD pipeline | Production-grade |

### Repository Structure Issues

- `src/data/` and `src/synthetic/` are duplicate packages with redundant generators — consolidate into `src/synthetic/`
- `src/app/__init__.py` and `src/core/contracts/__init__.py` are empty placeholder packages — remove
- `scripts/` naming is inconsistent (mix of numbered and named conventions)
- `ai_workspace/` is a research directory with no class structure; boundary with `scripts/` is not obvious

---

## 8. Final Agreed UI Observability Architecture

### Design Principle

The Observability + AI Investigation Center is a strictly **read-only** presentation and investigation layer. It surfaces data produced by the AI pipeline, the alert management system, and the Prometheus metrics stack. It never modifies system configuration, triggers model retraining, or interacts with any write-path component. It does not replace Grafana — it complements it at the AI pipeline investigation level.

### System Positioning

```
+----------------------------------+
|  UI Layer                        |
|  Observability + Investigation   |
|  Center (Streamlit / HTML)       |
+----------------------------------+
              |
              | HTTP / WebSocket
              |
+----------------------------------+
|  FastAPI Service (port 8000)     |
|  src/api/app.py                  |
|  src/api/routes.py               |
|  src/api/ui.py                   |
+----------------------------------+
       |              |
       |              +---------------------------+
       |                                          |
+------+------------+                 +-----------+---------+
| ProactiveMonitor  |                 | Prometheus (9090)   |
| Engine            |                 +---------------------+
| src/engine/       |                           |
| proactive_engine  |                 +-----------+---------+
|                   |                 | Grafana   (3000)    |
|  LogPreprocessor  |                 +---------------------+
|  BehaviorModel    |
|  AnomalyDetector  |
|  SeverityClassif. |
+------+------------+
       |
+------+------------+
| AlertManager      |
| src/alerts/       |
| manager.py        |
| (ring buffer)     |
+-------------------+
```

### Five UI Panels

---

**Panel 1 — System Status**

**Data source**: `GET /health`
**Content**: Status badge (healthy / degraded / unhealthy / unknown), uptime string, components table showing each registered component (pipeline, alert_manager, inference_engine). After Phase 7, `ProactiveMonitorEngine` registers each of the six AI pipeline stages as individual sub-checks.
**Refresh**: Every 30 seconds.
**Availability**: Ready now. No API changes required.

---

**Panel 2 — Live Alert Feed**

**Data sources**: `GET /alerts` (initial load), `GET /ws/alerts` (live push)
**Content**: Sortable, filterable alert table with one row per alert. Columns: Time, Service, Severity (badge), Score, Threshold, Score/Threshold ratio bar, Model, Alert ID.
Filter controls: severity (multi-select), service name (multi-select), time range.
New alerts from WebSocket are prepended with a brief highlight animation.
**Interaction**: Clicking a row sets that alert as the active investigation context and activates Panel 5.
**Availability**: `GET /alerts` is implemented. `GET /ws/alerts` must be added.

---

**Panel 3 — Score Timeline**

**Data source**: `GET /score/history`
**Content**: Time-series line chart of reconstruction error (risk_score) over time. X-axis: window timestamp. Y-axis: risk score. Horizontal reference line at anomaly threshold. Anomaly markers (red dots) at windows where `is_anomaly=True`. Service filter dropdown. Secondary bar chart showing severity distribution (Info / Warning / Critical count) in the same time window.
**Refresh**: Polled every 10 seconds for new windows.
**Availability**: `GET /score/history` must be added, backed by a new `_score_buffer` ring buffer in `Pipeline`.

---

**Panel 4 — Pipeline Component Status**

**Data source**: `GET /pipeline/status`
**Content**: Component table with one row per pipeline stage.

| Stage | Class | Status | Model File | Config |
|---|---|---|---|---|
| 1. NLP Embedding | `LogPreprocessor` | Loaded / Not loaded | `models/word2vec.model` | vec_dim=100 |
| 2. Sequence Data | `LogDataset` | Active / Standby | N/A (runtime) | window=20, stride=10 |
| 3. Behavior Model | `SystemBehaviorModel` | Loaded / Not loaded | `models/behavior_model.pt` | hidden_dim=128 |
| 4. Anomaly Detector | `AnomalyDetector` | Loaded / Not loaded | `models/anomaly_detector.pt` | threshold (from artifact) |
| 5. Severity Classifier | `SeverityClassifier` | Loaded / Not loaded | `models/severity_classifier.pt` | 3 classes |
| 6. Engine | `ProactiveMonitorEngine` | Active / Degraded | N/A | mode, uptime |

Configuration summary block below the table: `MODEL_MODE`, `WINDOW_SIZE`, `STRIDE`, `ALERT_COOLDOWN_SECONDS`, `DEMO_MODE`.
**Availability**: `GET /pipeline/status` must be added. An interim version backed by current `Pipeline` settings can be built before Phase 7. The full per-component breakdown is available only after Phase 7 when `ProactiveMonitorEngine.metrics_snapshot()` is implemented.

---

**Panel 5 — RAG Investigation Panel**

**Data sources**: `GET /alerts/{alert_id}`, `POST /query`, `GET /score/history`
**Activation**: Exclusively by selecting an alert in Panel 2. Never auto-activated.
**Content**: Three sections:
1. Alert evidence summary — full detail including evidence_window
2. Score context window — mini chart of reconstruction error in the 60-second window before and after the alert
3. AI investigation interface — text input for natural-language questions; response rendered as plain-language answer + evidence source list

Example operator questions:
- "Why did this alert fire?"
- "Has this service triggered critical alerts before?"
- "What was the reconstruction error trend before this alert?"
- "What model scored this window and what was the threshold?"

**RAG design principle**: RAG is an explanation layer, not a detection layer. It reads from already-committed alert and score data. It never writes to the alert buffer, the score buffer, or any pipeline component. All query handlers in `ui.py` are pure functions with no side effects.

**RAG backend upgrade path**: The current stub in `src/api/ui.py` uses hardcoded keyword matching. The upgrade queries three live sources: alert ring buffer (recent alerts for same service), score history ring buffer (reconstruction error trend), and the `evidence_window` dict from the selected alert. Template-based answer generation produces grounded responses without requiring an external LLM. A local LLM (e.g., `ollama`) can be added as a future enhancement without changing the `POST /query` interface contract.
**Availability**: Scaffolded now with current `POST /query` stub. `GET /alerts/{alert_id}` must be added. Full quality depends on Phase 7 completion.

---

### Required API Endpoints

| Endpoint | Method | Consumer Panel | Current Status |
|---|---|---|---|
| `/health` | GET | Panel 1 — System Status | Implemented |
| `/alerts` | GET | Panel 2 — Live Alert Feed | Implemented |
| `/metrics` | GET | Infrastructure / Grafana | Implemented |
| `/` | GET | Landing page | Implemented (HTML stub) |
| `/query` | POST | Panel 5 — RAG Investigation | Stub only — must be upgraded |
| `/ws/alerts` | WebSocket | Panel 2 — Live Alert Feed (push) | Not implemented |
| `/pipeline/status` | GET | Panel 4 — Pipeline Component Status | Not implemented |
| `/score/history` | GET | Panel 3 — Score Timeline | Not implemented |
| `/alerts/{alert_id}` | GET | Panel 5 — RAG Investigation (detail) | Not implemented |

### Recommended UI Technology

**Streamlit** is the recommended implementation technology for this project. It is Python-native, requires no JavaScript build toolchain, provides built-in chart support (`st.line_chart`, `st.plotly_chart`), handles state management via `st.session_state`, and runs as a separate process from the FastAPI server that calls the API over HTTP.

Streamlit belongs in `requirements-dev.txt`, not production `requirements.txt`. It is not included in the Docker image. It runs locally alongside the Docker Compose stack:

```bash
streamlit run src/ui/dashboard.py
```

The Streamlit dashboard imports only `streamlit`, `httpx`, `plotly.express`, and standard library modules. It never imports from `src/` directly. All data access is through HTTP calls to the running FastAPI service via `src/ui/api_client.py`.

**Grafana integration**: Do not replicate infrastructure metrics in Streamlit. Embed a link to the Grafana dashboard in the sidebar. The Streamlit dashboard focuses on AI pipeline observability (reconstruction errors, alert investigation, component state). Grafana handles infrastructure observability (event throughput, endpoint latency, resource utilization).

---

## 9. Approved Upgrade Additions

The following five upgrades have been reviewed, confirmed compatible with the current architecture, and approved for integration at their correct phases. They are additions to the original planning documents, not replacements.

---

### 9.1 Preprocessing Improvements

**Scope**: During Phase 2 implementation of `LogPreprocessor.clean()`, the text normalization patterns should be improved beyond the nine patterns currently in `TemplateMiner._SUBS`.

**Approved improvements**:
- IPv6 address normalization (current patterns handle IPv4 only)
- Additional timestamp format variants (ISO 8601, epoch milliseconds, log4j-style)
- Session ID, transaction ID, and block ID formats beyond the HDFS-specific `blk_` prefix
- Service name canonicalization (uppercase/lowercase variants, hyphen vs. underscore)
- Error code normalization (OS-level codes such as `ENOENT`, `EIO`, `ENOMEM`; Windows event IDs where applicable)

**Validation requirement**: Each new normalization pattern must be validated against actual samples from both BGL and HDFS log corpora before inclusion. Over-aggressive normalization that collapses semantically distinct tokens is a concrete risk.

**Integration point**: Phase 2 — implemented inside `LogPreprocessor.clean()`. Not a separate preliminary task.

---

### 9.2 FastText as Experimental Benchmark

**Scope**: FastText may be trained and benchmarked alongside Word2Vec during Phase 2. It is not the production default and must not replace Word2Vec without supporting performance evidence.

**Positioning**:
- Word2Vec is the primary embedding model as specified in `IMPLEMENTATION_ACTION_PLAN.md` Phase 2
- FastText is an optional, experimental parallel benchmark trained from the same log corpus
- Both models are available via `gensim>=4.3.0` (same library addition to `requirements.txt`)
- The `LogPreprocessor` class supports a `backend` parameter (`"word2vec"` | `"fasttext"`) to select the active model
- The default backend is always `"word2vec"` unless changed explicitly

**Promotion condition**: FastText may be promoted to the default only if a comparative evaluation after Phase 5 (`AnomalyDetector` complete) shows measurably better reconstruction error separability between normal and anomalous sequences on the BGL and HDFS validation sets.

**Why FastText is appealing for this project**: BGL logs contain tokens that escape normalization (residual hex values, composite node identifiers, device path fragments). FastText's character n-gram approach produces non-zero embeddings for out-of-vocabulary tokens. If normalization quality is high, this advantage diminishes — hence the requirement for evidence before promotion.

**What FastText is not**: It is not a replacement for Word2Vec, not a migration path, not a production-layer change without evidence, and not an input to LSTM, Autoencoder, or MLP design (all downstream stages are vector-agnostic once the embedding shape is fixed).

**Artifacts**: `models/fasttext.model` (experimental only; `models/word2vec.model` is the default)

**Integration point**: Phase 2 — trained as a side experiment after Word2Vec training script is confirmed working.

---

### 9.3 Fallback Strategy — Parallel Pipeline During Migration

**Scope**: The previous pipeline (IsolationForest baseline + causal Transformer) must remain available and operational throughout the entire AI refactor. The new autoencoder pipeline is added as a new parallel scoring mode, not as a direct replacement.

**Mechanism**: The `InferenceEngine` already supports multiple scoring modes via `MODEL_MODE` environment variable. The approved extension adds `autoencoder` as a fourth valid mode alongside the existing `baseline`, `transformer`, and `ensemble` modes.

**Operational benefits**:
- Zero-downtime migration: the system never has a period without a working scoring model
- Rollback capability: setting `MODEL_MODE=baseline` and restarting the container restores the previous behavior
- Comparative evaluation: both old and new modes can score the same input, enabling direct performance comparison
- Test continuity: the 22 `@pytest.mark.slow` tests that depend on `models/baseline.pkl` and `models/transformer.pt` continue passing throughout transition

**Guard**: Old model files (`models/baseline.pkl`, `models/transformer.pt`) must not be deleted until the new pipeline has been validated and a comparison report confirms the new architecture performs at least as well as the baseline on both BGL and HDFS datasets.

**Integration point**: Phase 5 (Autoencoder) — the fallback mode is already present; the guard is to not remove it during refactor phases.

---

### 9.4 Missing UI Endpoints

**Scope**: Four endpoints currently absent from `src/api/routes.py` must be added to support the five UI panels defined in `UI_OBSERVABILITY_INVESTIGATION_CENTER.md`.

All four endpoints are read-only. They do not modify any pipeline state. They must be added to `src/api/schemas.py` with new response schemas without modifying existing schema classes.

**Endpoint 1: `GET /pipeline/status`**
- **Consumer**: Panel 4 — Pipeline Component Status
- **Interim version** (before Phase 7): returns `Pipeline` mode, `window_size`, `stride`, `alert_cooldown_seconds`, `demo_mode` from settings
- **Full version** (after Phase 7): returns per-component load status from `ProactiveMonitorEngine.metrics_snapshot()`
- **Integration point**: Interim in Phase 7; full in Phase 8

**Endpoint 2: `GET /score/history`**
- **Consumer**: Panel 3 (Score Timeline), Panel 5 (RAG mini-chart)
- **Query parameters**: `n` (default 500), `service` (optional filter), `since` (optional Unix timestamp)
- **Backend requirement**: Add `_score_buffer: deque` to `Pipeline` (capacity via `SCORE_HISTORY_SIZE` env var, default 500); `process_event()` appends non-None `risk_result` to this buffer
- **Integration point**: Phase 7-8

**Endpoint 3: `GET /alerts/{alert_id}`**
- **Consumer**: Panel 5 — RAG Investigation (alert detail load)
- **Backend requirement**: Linear scan of `_alert_buffer` by `alert_id` (O(n), n <= 200 — acceptable); or a secondary `dict[str, dict]` lookup for O(1) access
- **Response schema**: Single `AlertSchema` object
- **Integration point**: Phase 8

**Endpoint 4: `GET /ws/alerts`**
- **Consumer**: Panel 2 — Live Alert Feed (live push)
- **Authentication**: API key passed as a query parameter (`?api_key=...`) since browser WebSocket connections cannot set custom headers
- **Backend requirement**: `asyncio.Queue` per connected client in `app.state`; `process_event()` calls a registered callback that enqueues new alerts to all active client queues; WebSocket handler consumes its queue and sends
- **Fallback**: `GET /alerts` REST polling serves as fallback if WebSocket is unavailable
- **Integration point**: Phase 8

**Implementation order** (as recommended by UIC Section 10):
1. `GET /pipeline/status` (interim) — unblocks Phase 1 UI Panel 4
2. `GET /score/history` — unblocks Phase 2 UI Panel 3
3. `GET /alerts/{alert_id}` — unblocks Phase 2 UI Panel 5
4. `GET /ws/alerts` — unblocks Phase 2 UI Panel 2 live push

---

### 9.5 Deferred Real-Server Deployment (Note Only)

A small real-server deployment hardening — adding a reverse proxy (nginx), TLS termination (HTTPS), and confirming API key authentication — has been reviewed and is architecturally sound.

**It is deferred to after Phase 8** for the following reasons:
- `IMPLEMENTATION_ACTION_PLAN.md` explicitly states "Docker Compose: No changes needed" during the AI refactor
- Introducing nginx and HTTPS certificate handling during the active AI refactor adds CI/CD complexity without contributing to the refactor goals
- API key authentication is already fully implemented via `AuthMiddleware`
- The existing Docker Compose stack is the correct deployment target throughout all AI pipeline phases

**When to implement**: After Phase 8 is complete and all 233+ tests pass consistently, a deployment hardening task should add an `nginx:alpine` service to `docker-compose.yml` as a TLS-terminating reverse proxy. WebSocket upgrade headers (`proxy_pass`, `Upgrade`, `Connection`) must be explicitly configured for the `/ws/alerts` endpoint.

**No Kubernetes**: The target deployment environment remains Docker Compose. Kubernetes is out of scope.

---

## 10. Experimental and Optional Components

These items are recognized as potentially valuable but are not part of the core required architecture. They must not block or delay Phases 1-8.

| Component | Description | When Applicable |
|---|---|---|
| FastText model | Experimental embedding benchmark; trained alongside Word2Vec in Phase 2. May be promoted to default only with performance evidence from Phase 5 comparative evaluation. | Phase 2 experiment; Phase 5 evaluation |
| Local LLM for RAG | A local language model (e.g., via `ollama`) can replace the template-based answer generation in `POST /query` to produce richer investigation answers. The `POST /query` interface contract does not change. | Post-Phase 8; optional enhancement |
| Kafka / Logstash ingestion | A streaming log adapter to consume from Kafka or Logstash instead of HTTP POST. The current HTTP ingest path is adequate for the refactor scope. | Post-Phase 8; future capability |
| Real notification delivery | The `N8nWebhookClient` is implemented as a dry-run outbox. Activating real Slack or email notifications requires configuring the n8n endpoint. | Post-Phase 8; optional activation |
| Grafana dashboard expansion | New Prometheus metrics (`reconstruction_error_histogram`, `severity_info_total`, etc.) added in Phase 7 should be visualized in new Grafana panels. | Phase 8 or post-Phase 8 |

---

## 11. Deferred Items

These items are explicitly postponed. They are not part of the immediate implementation scope and must not be introduced before Phase 8 is stable.

| Item | Reason for Deferral | Target Phase |
|---|---|---|
| nginx reverse proxy + HTTPS | Adds CI complexity during active AI refactor; API auth already implemented | Post-Phase 8 |
| FastText as production default | No performance evidence yet; evidence required from Phase 5 comparative evaluation | Post-Phase 5 (conditional) |
| Kafka / Logstash streaming input | HTTP POST is sufficient for refactor scope; streaming adapters are architectural extensions | Post-Phase 8 |
| Real Slack/Email notifications | n8n stub is adequate for current scope | Post-Phase 8 |
| React frontend | Overengineered for current UI requirements; Streamlit is the correct choice | Reconsider only if UI scope escalates to service topology maps |
| Gradio UI | ML demo alternative to Streamlit; not needed given Streamlit recommendation | Optional; post-Phase 8 |
| Human-reviewed severity labels | Auto-labeling from `AlertPolicy` ratio rule is the initial approach; human review improves MLP quality | Post-Phase 6; ongoing improvement |
| Kubernetes deployment | Out of scope; Docker Compose is the target environment | Not applicable to this project scope |

---

## 12. Architecture Constraints and Non-Negotiables

The following rules must not be broken at any phase of implementation. Any proposed change that would violate these constraints must be rejected.

| Constraint | Reason |
|---|---|
| **LSTM is the main sequence model** | Defined in PRR as the Stage 3 architecture. Not replaceable with Transformer or RNN as the primary |
| **Word2Vec is the default embedding** | Defined in IAP Phase 2. FastText may only appear as an experimental benchmark |
| **Transformers are NOT the MVP path** | The existing `NextTokenTransformerModel` remains as a fallback only |
| **Doc2Vec is not part of this architecture** | Not defined in PRR or IAP; must not be introduced |
| **UI is strictly read-only** | UIC design principle: the UI surfaces data but does not modify configuration, trigger retraining, or interact with write paths |
| **No admin control panel** | The UI is an observability and investigation interface only |
| **Docker Compose is the deployment target** | No Kubernetes; no major infrastructure redesign |
| **Old pipeline must remain available during transition** | IsolationForest and Transformer stay as fallback modes throughout all phases |
| **Old model files must not be deleted** | Until the new pipeline is validated on BGL and HDFS datasets |
| **233 existing tests must pass throughout** | All refactor phases must maintain a green test suite; no test may be deleted without replacement |
| **New model-dependent tests must be marked `@pytest.mark.slow`** | CI fast suite must run in under 15 seconds; `pytest -m "not slow"` is the CI command |
| **`src/api/routes.py` existing endpoints are stable** | New endpoints are additive; existing endpoint contracts must not change |
| **Existing schema classes must not be modified** | New response schemas are added to `src/api/schemas.py` without touching existing classes |
| **No non-ASCII characters in print/log output** | Console encoding is cp1255 on this platform; ASCII-only in all `print()` and `logger.*()` calls |

---

## 13. Consolidated Implementation Roadmap

This roadmap merges the phase-by-phase plan from `IMPLEMENTATION_ACTION_PLAN.md`, the structural cleanup plan from `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md`, and the UI development phases from `UI_OBSERVABILITY_INVESTIGATION_CENTER.md`. Approved upgrade additions are integrated at their correct positions.

---

### Phase 1 — Architecture Alignment and Structure

**Objective**: Establish the correct class names, module boundaries, and entrypoint. No AI logic yet — this phase is about naming, structure, and ensuring all six required class names exist and are importable.

**Why first**: The requirements document defines a class-name contract. Without the correct names and locations, all subsequent work is structurally misaligned.

**Tasks**:
1. Create `src/preprocessing/__init__.py` + `log_preprocessor.py` — stub `LogPreprocessor` class with method signatures but no logic
2. Create `src/dataset/__init__.py` + `log_dataset.py` — stub `LogDataset(torch.utils.data.Dataset)` class
3. Create `src/modeling/behavior_model.py` — stub `SystemBehaviorModel` class
4. Create `src/modeling/anomaly_detector.py` — stub `AnomalyDetector` class
5. Create `src/modeling/severity_classifier.py` — stub `SeverityClassifier` class
6. Create `src/engine/__init__.py` + `proactive_engine.py` — stub `ProactiveMonitorEngine` class
7. Create `main.py` at project root — imports all six classes, starts uvicorn
8. Delete empty `src/app/` and `src/core/contracts/` packages
9. Consolidate `src/data/` into `src/synthetic/` (resolve duplication)
10. Standardize `scripts/` naming to `stage_XX_name.py` convention
11. Run `pytest -m "not slow"` — all 211 fast tests must still pass

**Expected outcome**: All six required class names exist and are importable. `main.py` starts the server. No tests broken.

---

### Phase 2 — NLP Pipeline (LogPreprocessor + Word2Vec)

**Objective**: Implement full text cleaning, word tokenization, Word2Vec embedding training, and mean pooling. This is the foundation of the entire new AI pipeline — all downstream components depend on the quality of these embeddings.

**Tasks**:
1. Add `gensim>=4.3.0` to `requirements.txt`
2. Implement `LogPreprocessor.clean()`:
   - Port base patterns from `TemplateMiner._SUBS` as the starting point
   - **Add approved preprocessing improvements**: IPv6 normalization, additional timestamp format variants, session/transaction ID patterns, service name canonicalization, error code normalization
   - Validate each new pattern against actual BGL and HDFS log samples before including
3. Implement `LogPreprocessor.tokenize()` — word-level split of cleaned text
4. Implement `LogPreprocessor.train_embeddings()` — train Word2Vec on `events_unified.csv` message column; use existing 1M-row sample (`data/processed/events_sample_1m.csv`) for manageable memory
5. Implement `LogPreprocessor.embed()` — mean-pool word vectors for a single log line
6. Implement `LogPreprocessor.save()` and `LogPreprocessor.load()` — save Word2Vec model to `models/word2vec.model`
7. Write training script `scripts/train_embeddings.py`
8. Save embedding cache: `data/intermediate/log_embeddings.npy`
9. Write unit tests: `tests/unit/test_log_preprocessor.py`
10. **Approved experimental addition**: After Word2Vec training is confirmed working, train FastText on the same corpus. Add `backend` parameter to `LogPreprocessor` (`"word2vec"` default, `"fasttext"` optional). Save `models/fasttext.model`. Document comparison results in `docs/fasttext_comparison_notes.md` for later evaluation.

**Expected outcome**: `LogPreprocessor` produces a 100-dim float vector for any log line. `models/word2vec.model` artifact on disk. `models/fasttext.model` available as an experimental benchmark.

---

### Phase 3 — Sequence Dataset (LogDataset)

**Objective**: Implement `LogDataset` as a proper `torch.utils.data.Dataset` over embedded log windows. Produce a working `DataLoader` yielding 3D float tensors.

**Tasks**:
1. Implement `LogDataset.__init__()` — accepts list of embedded log arrays, labels, window size, stride
2. Implement `LogDataset.__len__()` and `LogDataset.__getitem__(idx)` — returns `(FloatTensor[seq_len, vec_dim], label)`
3. Add `LogDataset.from_csv()` class method — loads embedding cache, builds windows
4. Add `make_dataloaders(dataset, batch_size, val_split)` factory function using `torch.utils.data.DataLoader`
5. Write unit tests: `tests/unit/test_log_dataset.py`

**Expected outcome**: `DataLoader` yields 3D float tensors `[32, 20, 100]` ready for LSTM input. All existing tests still pass.

**Dependency**: Phase 2 complete (Word2Vec model must exist).

---

### Phase 4 — LSTM Behavior Model (SystemBehaviorModel)

**Objective**: Implement `SystemBehaviorModel` as an LSTM encoder that produces a context vector summarizing a log window.

**Tasks**:
1. Create `LSTMConfig` dataclass: `input_dim`, `hidden_dim`, `num_layers`, `dropout`, `learning_rate`, `max_epochs`, `patience`
2. Implement `SystemBehaviorModel.forward()` — `nn.LSTM` processing 3D input; return final hidden state as context vector
3. Implement `SystemBehaviorModel.save()` and `SystemBehaviorModel.load()` — mirror pattern from `NextTokenTransformerModel`
4. Implement training loop in `scripts/train_behavior_model.py`:
   - Train on normal sequences only (label=0)
   - Use AdamW + CosineAnnealingLR (adapt from existing `Trainer` in `src/modeling/transformer/trainer.py`)
5. Save trained model to `models/behavior_model.pt`
6. Write unit tests: `tests/unit/test_behavior_model.py`; mark as `@pytest.mark.slow`

**Expected outcome**: `SystemBehaviorModel` produces context vectors `[batch_size, hidden_dim]` from DataLoader batches.

**Dependency**: Phase 3 complete (DataLoader must be working).

---

### Phase 5 — Autoencoder Anomaly Engine (AnomalyDetector)

**Objective**: Implement `AnomalyDetector` as a Denoising Autoencoder. Integrate into `InferenceEngine` as the new `autoencoder` scoring mode.

**Tasks**:
1. Implement `AnomalyDetector` with separate Encoder and Decoder `nn.Sequential` blocks
2. Implement `AnomalyDetector.forward()` — Encoder compresses context vector to latent space; Decoder reconstructs; return `(reconstructed, latent)`
3. Implement `AnomalyDetector.reconstruction_error()` — MSE between original and reconstructed
4. Implement training loop in `scripts/train_anomaly_detector.py`:
   - Train on normal context vectors from `SystemBehaviorModel`
   - Use MSE loss
5. Implement `AnomalyDetector.fit_threshold()` — 95th percentile of normal reconstruction errors on validation set
6. Save model to `models/anomaly_detector.pt` and threshold to `artifacts/threshold_autoencoder.json`
7. Wire into `InferenceEngine`: add `score_autoencoder(context_vector)` method — the new `autoencoder` mode
8. **Approved fallback strategy**: confirm `MODEL_MODE=baseline` and `MODEL_MODE=transformer` continue to work unchanged; do not delete `models/baseline.pkl` or `models/transformer.pt`
9. Write unit tests: `tests/unit/test_anomaly_detector.py`; mark as `@pytest.mark.slow`
10. **FastText evaluation**: compare FastText vs. Word2Vec embeddings by running both through the trained LSTM + Autoencoder and comparing reconstruction error separability on BGL/HDFS validation sets; document findings in `docs/fasttext_comparison_notes.md`

**Expected outcome**: `AnomalyDetector` flags anomalous sequences via reconstruction error. `InferenceEngine` has a new `autoencoder` mode alongside `baseline` and `transformer`. FastText comparison results available to inform the production embedding decision.

**Dependency**: Phase 4 complete (context vectors must be available).

---

### Phase 6 — Severity Classifier (SeverityClassifier)

**Objective**: Implement `SeverityClassifier` as a trained MLP that replaces the hard-coded severity ratio rule.

**Tasks**:
1. Generate severity training labels: apply `AlertPolicy.classify_severity()` ratio rule to reconstruction errors on anomaly windows to auto-label each window as info/warning/critical (documented approximation; human review is a future improvement)
2. Implement `SeverityClassifier` MLP: `Linear -> ReLU -> Dropout -> Linear -> ReLU -> Dropout -> Linear -> Softmax`; input dim = `latent_dim + 1`; output dim = 3
3. Implement `SeverityClassifier.predict(latent, error)` — returns `"info"` | `"warning"` | `"critical"`
4. Implement training loop in `scripts/train_severity_classifier.py`; use CrossEntropyLoss + AdamW
5. Save model to `models/severity_classifier.pt`
6. Replace `AlertPolicy.classify_severity()` call with `SeverityClassifier.predict()` in `src/alerts/models.py:AlertPolicy.risk_to_alert()`
7. Write unit tests: `tests/unit/test_severity_classifier.py`; mark as `@pytest.mark.slow`

**Expected outcome**: Severity is assigned by a trained MLP. Alert severity output is probabilistic. All existing tests pass.

**Dependency**: Phase 5 complete (latent vectors and reconstruction errors must be available).

---

### Phase 7 — Engine Integration (ProactiveMonitorEngine + New Metrics)

**Objective**: Wire all six classes into `ProactiveMonitorEngine` and connect to the FastAPI pipeline. Add new Prometheus metrics. Add interim `GET /pipeline/status` endpoint.

**Tasks**:
1. Implement `ProactiveMonitorEngine.load_models()` — load `LogPreprocessor`, `SystemBehaviorModel`, `AnomalyDetector`, `SeverityClassifier`; retain `BaselineAnomalyModel` and `NextTokenTransformerModel` as fallback options
2. Implement `ProactiveMonitorEngine.process_event(event)` — full pipeline: clean text -> embed -> buffer -> context vector -> reconstruction error -> severity -> alert
3. Update `src/api/pipeline.py` to instantiate `ProactiveMonitorEngine` instead of `InferenceEngine` directly
4. Add new Prometheus metrics to `MetricsRegistry`: `reconstruction_error_histogram`, `severity_info_total`, `severity_warning_total`, `severity_critical_total`
5. Update `Settings`: add `MODEL_MODE=autoencoder` as a valid mode
6. **Add interim `GET /pipeline/status` endpoint** — returns current `Pipeline`/`ProactiveMonitorEngine` mode, window/stride settings, demo mode flag, and whether model artifacts loaded successfully; backed by the existing Pipeline class initially, upgraded to `ProactiveMonitorEngine.metrics_snapshot()` once the engine is integrated
7. **Add `_score_buffer` to `Pipeline`** — `deque(maxlen=SCORE_HISTORY_SIZE)`; `process_event()` appends `risk_result` to this buffer when a window is emitted
8. Run the full test suite — all 233 tests must pass
9. Run Docker Compose smoke test end-to-end
10. Update `scripts/stage_07_run_api.py` and `main.py` to use the new engine

**Expected outcome**: Full six-stage pipeline is live behind the FastAPI server. Existing tests pass. Docker stack starts cleanly. `GET /pipeline/status` returns engine status. `_score_buffer` is populated.

---

### Phase 8 — UI Layer and Remaining API Endpoints

**Objective**: Implement the Observability + AI Investigation Center (Streamlit), add the remaining three required API endpoints, and upgrade the RAG backend.

**Tasks**:

**API layer (complete the four missing endpoints)**:
1. Upgrade `GET /pipeline/status` to full version — backed by `ProactiveMonitorEngine.metrics_snapshot()` returning per-component load status, artifact paths, and threshold values
2. Add `GET /score/history` endpoint — returns `_score_buffer` contents filtered by optional `n`, `service`, and `since` query parameters; define `ScoreHistoryResponse` schema in `src/api/schemas.py`
3. Add `GET /alerts/{alert_id}` endpoint — linear scan of `_alert_buffer` by `alert_id`; returns single `AlertSchema`
4. Add `GET /ws/alerts` WebSocket endpoint — asyncio-based per-client queue; `process_event()` registers callback that enqueues new alerts to all active client queues
5. Add corresponding unit tests for all four endpoints; add integration smoke tests to `tests/integration/test_smoke_api.py`

**RAG backend upgrade**:
6. Upgrade `POST /query` in `src/api/ui.py` — replace static knowledge base with live query over alert ring buffer, score history buffer, and evidence window data; extend request schema with optional `context` block; template-based answer generation using evidence-driven templates

**Streamlit UI**:
7. Add `streamlit` and `plotly` to `requirements-dev.txt`
8. Create `src/ui/__init__.py`, `src/ui/api_client.py` (typed httpx wrapper for all API calls)
9. Create `src/ui/components/` with `status.py`, `alert_feed.py`, `timeline.py`, `pipeline.py`, `rag.py`
10. Create `src/ui/dashboard.py` — main Streamlit application connecting all five panels; reads only from the FastAPI API; never imports from `src/` directly
11. Create `src/ui/README.md` — startup instructions

**Verification**:
12. Run the full test suite — all 233+ tests must pass
13. Run Docker Compose smoke test
14. Confirm Streamlit dashboard launches, connects to the running FastAPI service, and all five panels render with live data

**Expected outcome**: The Observability + AI Investigation Center is operational. All five UI panels are functional. All four previously missing endpoints are implemented and tested. RAG investigation returns evidence-grounded answers.

---

### Post-Phase 8 — Deployment Hardening (Deferred)

After Phase 8 is confirmed stable:

1. Add `nginx:alpine` service to `docker-compose.yml` as TLS-terminating reverse proxy
2. Configure nginx for HTTP-to-HTTPS redirect, WebSocket upgrade headers (`Upgrade`, `Connection`), and API proxy pass to `api:8000`
3. Provision TLS certificates (self-signed for local, Let's Encrypt for production with a domain name)
4. Update CI smoke test to handle HTTPS
5. Write deployment documentation in `docs/deployment_guide.md`

This phase has no dependency on any AI model training output. It is a pure deployment infrastructure task that can proceed independently once the system is stable.

---

## 14. Final Recommendation

### The Nature of This Project

This is a **targeted replacement of the AI learning pipeline with full preservation of the production infrastructure**. It is not a full rewrite and not a superficial rename. The engineering effort is concentrated in building four new AI components (Stages 1-5) and one integration class (Stage 6) while keeping the entire API, alerting, observability, and deployment infrastructure unchanged.

### What to Preserve

The existing IsolationForest model, causal Transformer model, and their corresponding scoring paths in `InferenceEngine` are not deleted. They remain as operational fallbacks throughout all phases, enabling rollback, comparison, and test continuity. They should only be deprecated and eventually removed after a documented comparative evaluation confirms the new autoencoder pipeline performs as well or better on both BGL and HDFS datasets.

### What to Replace

The integer token ID representation at the core of the current pipeline is replaced by float embedding vectors. This is the deepest architectural change — it propagates through `SequenceBuffer`, `InferenceEngine.ingest()`, and all training scripts. The replacement is implemented as a new parallel scoring mode (`autoencoder`), not as a modification of existing modes. At no point during the transition is the system left without a working scoring model.

### The Critical Path

The six AI phases are a sequential dependency chain. Phase 3 (LogDataset) cannot run without Phase 2 (Word2Vec). Phase 4 (LSTM) cannot train without Phase 3. Phase 5 (Autoencoder) cannot train without Phase 4. Phase 6 (MLP) cannot train without Phase 5. Phase 7 (ProactiveMonitorEngine) cannot be wired without Phases 1-6. The primary risk is not any individual implementation challenge — it is attempting to shortcut this chain or to run multiple phases simultaneously before each predecessor is confirmed working.

### Priority Order for Implementation

1. Phase 1 (Architecture Alignment) — low risk; enables everything else
2. Phase 2 (LogPreprocessor + Word2Vec) — foundational; determines embedding quality for all downstream models
3. Phase 3 (LogDataset) — enables model training
4. Phase 4 (SystemBehaviorModel LSTM) — core sequence model
5. Phase 5 (AnomalyDetector Autoencoder) — core anomaly signal; also triggers FastText evaluation
6. Phase 6 (SeverityClassifier MLP) — completes the AI pipeline
7. Phase 7 (ProactiveMonitorEngine Integration) — wires the pipeline to production; adds interim `GET /pipeline/status`
8. Phase 8 (UI Layer + Remaining Endpoints) — makes the system observable and investigable
9. Post-Phase 8 (Deployment Hardening) — HTTPS, reverse proxy; no dependency on AI model work

### Stability Principle

Every phase must leave the system in a deployable, testable state. The `pytest -m "not slow"` fast suite must remain green throughout. The Docker Compose stack must start and serve `/health` successfully at every phase boundary. No phase may end with broken tests, missing imports, or a non-starting API server.

The infrastructure layer — FastAPI, AlertManager, Prometheus, Grafana, Docker, CI — is the project's greatest asset. It provides a stable, tested foundation on which the new AI pipeline can be built incrementally. Every decision during the refactor must protect this foundation.

---

*This is a consolidated reference document. The four original source documents remain unchanged and authoritative. This document merges their content for clarity and adds five approved upgrade integration points. No content from the originals has been omitted or contradicted.*

*Original sources:*
- *`IMPLEMENTATION_ACTION_PLAN.md`*
- *`PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md`*
- *`REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md`*
- *`UI_OBSERVABILITY_INVESTIGATION_CENTER.md`*
