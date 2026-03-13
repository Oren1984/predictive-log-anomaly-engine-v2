# System Architecture Overview
## Predictive Log Anomaly Engine

**Document Type:** High-Level Architecture Reference
**Assembled from:**
- `PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md` — Section 4 (Architecture Overview)
- `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md` — Sections 1, 2, 3
- `IMPLEMENTATION_ACTION_PLAN.md` — Section 5 (Target Architecture)

The original source documents remain unchanged. This file is a structural overview only.

---

## 1. Six-Stage Pipeline Overview

The system is built as a six-stage AI pipeline. Each stage has one responsible class.

| Phase | Objective | Technologies | OOP Implementation |
|---|---|---|---|
| NLP Embedding | Convert raw logs to vector space | Tokenization, Word2Vec, FastText | `LogPreprocessor` |
| Sequence Data Prep | Prepare time windows for neural networks | PyTorch Tensors, DataLoaders | `LogDataset` |
| Sequence Modeling | Learn behavior patterns over time | LSTM, RNN | `SystemBehaviorModel` |
| Anomaly Detection | Detect abnormal sequences | Denoising Autoencoders | `AnomalyDetector` |
| Severity Classification | Prioritize alerts | MLP, Adam Optimizer, Dropout | `SeverityClassifier` |
| AIOps Infrastructure | Deploy monitoring system | Prometheus, Grafana | `ProactiveMonitorEngine` |

---

## 2. Data Flow Through the Pipeline

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

---

## 3. Module Interaction Flow (Runtime)

```
Raw Log Line
    |
    v  [src/parsing/parsers.py]
LogEvent (timestamp, service, level, message)
    |
    v  [src/preprocessing/log_preprocessor.py]
Float vector [vec_dim=100]
    |
    v  [src/dataset/log_dataset.py]  (training path)
3D Tensor [batch=32, seq=20, vec=100]
    |
    v  [src/modeling/behavior_model.py]
Context Vector [hidden_dim]
    |
    v  [src/modeling/anomaly_detector.py]
reconstruction_error (float) + latent_vector [latent_dim]
    |
    v  [src/modeling/severity_classifier.py]
Severity probabilities [Info%, Warning%, Critical%]
    |
    v  [src/engine/proactive_engine.py]
    |       |                    |
    |       v                    v
    |  MetricsRegistry      AlertManager
    |  (Prometheus)         (dedup+cooldown)
    |                            |
    v                            v
RiskResult                    Alert
    |                            |
    v                            v
 /ingest response           /alerts buffer
```

---

## 4. Target Folder Structure

```
predictive-log-anomaly-engine/
|
|-- src/
|   |-- preprocessing/
|   |   |-- __init__.py
|   |   |-- log_preprocessor.py       # LogPreprocessor (Stage 1)
|   |
|   |-- dataset/
|   |   |-- __init__.py
|   |   |-- log_dataset.py            # LogDataset(Dataset) (Stage 2)
|   |
|   |-- modeling/
|   |   |-- __init__.py
|   |   |-- behavior_model.py         # SystemBehaviorModel LSTM (Stage 3)
|   |   |-- anomaly_detector.py       # AnomalyDetector Autoencoder (Stage 4)
|   |   |-- severity_classifier.py    # SeverityClassifier MLP (Stage 5)
|   |   |-- baseline/                 # Keep existing IsolationForest (fallback)
|   |   |-- transformer/              # Keep existing Transformer (fallback)
|   |
|   |-- engine/
|   |   |-- __init__.py
|   |   |-- proactive_engine.py       # ProactiveMonitorEngine (Stage 6)
|   |
|   |-- runtime/
|   |   |-- inference_engine.py       # Keep; rewire to new models
|   |   |-- sequence_buffer.py        # Keep as-is
|   |   |-- types.py                  # Keep as-is
|   |
|   |-- api/
|   |   |-- app.py                    # Keep as-is
|   |   |-- routes.py                 # Keep as-is
|   |   |-- schemas.py                # Keep as-is
|   |   |-- settings.py               # Keep as-is
|   |   |-- pipeline.py               # Rewire to ProactiveMonitorEngine
|   |   |-- ui.py                     # Keep; upgrade in Phase 8
|   |
|   |-- alerts/
|   |   |-- manager.py                # Keep as-is
|   |   |-- models.py                 # Keep; replace classify_severity in Phase 6
|   |   |-- n8n_client.py             # Keep; activate in Phase 7
|   |
|   |-- observability/
|   |   |-- metrics.py                # Keep; add new metrics for new models
|   |   |-- logging.py                # Keep as-is
|   |
|   |-- parsing/
|   |   |-- parsers.py                # Keep; feeds LogPreprocessor
|   |   |-- tokenizer.py              # Keep; used by explain()
|   |   |-- template_miner.py         # Keep; logic reused in LogPreprocessor
|   |
|   |-- sequencing/
|   |   |-- builders.py               # Keep for runtime streaming path
|   |   |-- models.py                 # Keep (Sequence dataclass)
|   |   |-- splitter.py               # Keep
|   |
|   |-- synthetic/                    # Keep; consolidate src/data/ into here
|   |-- security/                     # Keep as-is
|   |-- health/                       # Keep as-is
|   |-- data_layer/                   # Keep as-is
|
|-- main.py                           # NEW: single entrypoint
|-- scripts/                          # Training CLI scripts (renamed consistently)
|-- tests/                            # Keep all 233 tests; add new ones per phase
|-- models/                           # Artifact storage (add new model files here)
|-- artifacts/                        # JSON artifacts (vocab, thresholds)
|-- data/                             # Raw, processed, intermediate data
|-- templates/                        # HTML UI
|-- prometheus/, grafana/             # No changes
|-- Dockerfile, docker-compose.yml    # No changes
|-- requirements.txt                  # Add: gensim
|-- pyproject.toml                    # No changes
```

---

## 5. Existing Infrastructure Stack

The following infrastructure components are already production-ready and require no changes during the AI pipeline refactor:

- `MetricsRegistry`: Prometheus counters and histograms (`ingest_events_total`, `alerts_total`, `ingest_latency_seconds`, etc.)
- `MetricsMiddleware`: HTTP middleware recording request latency
- Grafana dashboard: `stage08_api_observability.json` (5 panels)
- Prometheus scrape config: `prometheus/prometheus.yml`
- Docker Compose: `api:8000`, `prometheus:9090`, `grafana:3000`

---

## 6. Current vs. Required Alignment

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

**Summary**: The infrastructure layer (API, monitoring, Docker, CI) is well-aligned. The ML/AI pipeline layer is architecturally incompatible with the requirements and requires a complete replacement of the learning components.

---

## 7. OOP Class Boundaries (Target)

```
src/
|-- preprocessing/
|   |-- log_preprocessor.py   # LogPreprocessor (Stage 1)
|-- dataset/
|   |-- log_dataset.py        # LogDataset(torch.utils.data.Dataset) (Stage 2)
|-- modeling/
|   |-- behavior_model.py     # SystemBehaviorModel (LSTM/RNN) (Stage 3)
|   |-- anomaly_detector.py   # AnomalyDetector (Autoencoder) (Stage 4)
|   |-- severity_classifier.py# SeverityClassifier (MLP) (Stage 5)
|-- engine/
|   |-- proactive_engine.py   # ProactiveMonitorEngine (Stage 6)
|-- api/                      # (keep as-is)
|-- alerts/                   # (keep as-is)
|-- observability/            # (keep as-is)
|-- runtime/                  # (keep as-is, wire to new models)
main.py                       # Single entrypoint
```
