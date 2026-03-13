# Architecture Review

**Project:** Predictive Log Anomaly Engine
**Date:** 2026-03-04
**Stage:** 09 - Repository Documentation Finalization

---

## 1. System Architecture Overview

The Predictive Log Anomaly Engine is a multi-stage, containerized pipeline for detecting anomalies
in structured system log streams. It processes raw log data from two publicly available datasets
(HDFS and BGL), trains multiple anomaly detection models, and exposes a real-time REST API for
streaming event ingestion, risk scoring, alert generation, and observability.

The system is designed around the principle of **stage separation**: each pipeline step is an
independent, reproducible unit with clearly defined inputs, outputs, and reports. This makes
the system auditable, debuggable, and extensible.

### High-Level Architecture

```
+---------------------------------------------------------------+
|                    External Interface Layer                    |
|                                                               |
|   Browser (Demo UI)     n8n Webhooks     Prometheus Scraper   |
+----------------+----------------+------------------+-----------+
                 |                |                  |
+----------------v----------------v------------------v-----------+
|                        REST API Layer (Stage 7)                |
|                                                               |
|  POST /ingest   GET /alerts   GET /health   GET /metrics      |
|  GET /          POST /query                                   |
|                                                               |
|  AuthMiddleware | MetricsMiddleware | HealthChecker           |
+------------------------+-----------------------------------------+
                         |
+------------------------v-----------------------------------------+
|                    Pipeline Container (Stage 7)                   |
|                                                                   |
|   InferenceEngine        AlertManager        N8nWebhookClient     |
|   (Stage 5)              (Stage 6)           (Stage 6)            |
+-----+------------------+------------------------------------------+
      |                  |
+-----v------+    +------v-------+
|  Sequence  |    |  Alert Ring  |
|  Buffer    |    |  Buffer      |
| (per-key)  |    | (deque 200)  |
+-----+------+    +--------------+
      |
+-----v--------------------------------------------------+
|                ML Scoring Layer (Stage 5)              |
|                                                        |
|  BaselineFeatureExtractor + IsolationForest (Stage 24) |
|  NextTokenTransformerModel + AnomalyScorer (Stage 4)   |
|  Ensemble: normalized weighted combination             |
+--------------------------------------------------------+

+--------------------------------------------------------+
|              Offline Training Pipeline                  |
|                                                        |
|  Stage 21: Sampling      Stage 22: Template Mining     |
|  Stage 23: Sequences     Stage 24: Baseline Model      |
|  Stage 25: Evaluation    Stage 26: Supervised Model    |
+--------------------------------------------------------+

+--------------------------------------------------------+
|              Observability Stack (Stage 8)             |
|                                                        |
|  Prometheus (port 9090)   Grafana (port 3000)          |
|  /metrics endpoint        5 pre-built panels           |
+--------------------------------------------------------+
```

---

## 2. Component Responsibilities

### 2.1 Data Layer

| Component | Location | Responsibility |
|-----------|----------|---------------|
| Raw datasets | `data/raw/` | Original HDFS and BGL log files |
| Unified events | `data/processed/events_unified.csv` | 15.9M rows, normalized format |
| Sampled events | `data/intermediate/` | 1M-row working sample |
| Processed artifacts | `data/intermediate/*.parquet` | Tokenized events, sequence files |
| Trained models | `data/models/` | IsolationForest and LogReg pickle files |

### 2.2 Offline Pipeline (ai_workspace/)

| Stage | Component | Key Output |
|-------|-----------|-----------|
| 21 | Data Sampling | 1M event sample |
| 22 | Template Mining | 7,833 log templates; `events_with_templates.csv` |
| 23 | Sequence Builder | 495,405 sessions x 407 features; `session_features_v2.csv` |
| 24 | Baseline Model | `isolation_forest_v2.pkl`; `session_scores_v2.csv` |
| 25 | Evaluation | ROC/PR curves, confusion matrices, evaluation report |
| 26 | Supervised Model | `hdfs_supervised_best_v2.pkl` (LogReg-L2) |

### 2.3 Runtime Source (src/)

| Package | Location | Responsibility |
|---------|----------|---------------|
| `src/data/` | Data models | LogEvent definition, synthetic generator, scenario builder |
| `src/parsing/` | Stage 2 runtime | Template miner, tokenizer for live events |
| `src/sequencing/` | Stage 3 runtime | Sequence builders and splitters |
| `src/modeling/baseline/` | Stage 4 baseline | BaselineFeatureExtractor, BaselineAnomalyModel |
| `src/modeling/transformer/` | Stage 4 transformer | NextTokenTransformerModel, AnomalyScorer |
| `src/runtime/` | Stage 5 | InferenceEngine, SequenceBuffer, RiskResult |
| `src/alerts/` | Stage 6 | AlertManager, Alert, AlertPolicy, N8nWebhookClient |
| `src/api/` | Stage 7 | FastAPI app, routes, pipeline container, settings, UI |
| `src/health/` | Stage 7 | HealthChecker |
| `src/security/` | Stage 7 | AuthMiddleware (X-API-Key) |
| `src/observability/` | Stage 7 | MetricsRegistry, MetricsMiddleware, logging |

---

## 3. Data Flow Through Pipeline Stages

### 3.1 Offline Training Flow

```
Raw HDFS Logs (11.2M rows) + Raw BGL Logs (4.7M rows)
        |
        | [Stage 20/scripts] Parse and normalize
        v
events_unified.csv (15.9M rows: timestamp, dataset, session_id, message, label)
        |
        | [Stage 21] Sample 1M rows
        v
Sampled events (1M rows)
        |
        | [Stage 22] 9-step regex pipeline
        |   BLK/TS/IP/DATE/NODE/PATH/HEX/NUM/whitespace substitution
        v
events_with_templates.csv (1M rows + template_id + template_text)
templates.csv (7,833 unique templates, counts, anomaly_rate)
        |
        | [Stage 23] Group by session_id
        |   Build feature vectors: 7 meta + 100 tid_raw + 100 tid_norm
        |                          + 100 bigram_raw + 100 bigram_norm = 407 features
        v
session_sequences_v2.csv (495,405 sessions x 6 cols)
session_features_v2.csv  (495,405 sessions x 407 features)
        |
        | [Stage 24] IsolationForest (n_estimators=300)
        |   F1-optimal threshold scan (300 candidates)
        v
isolation_forest_v2.pkl (1826 KB)
session_scores_v2.csv (session_id, dataset, label, score, pred_overall, pred_by_dataset)
        |
        | [Stage 25] Evaluate on test split
        v
ROC curve, PR curve, confusion matrices, evaluation report
Overall: ROC=0.5632, PR=0.2127; BGL F1=0.965; HDFS F1=0.047
        |
        | [Stage 26] HDFS-specific LogReg-L2
        |   Train on HDFS subset (323K train / 40K val / 40K test)
        v
hdfs_supervised_best_v2.pkl (13.6 KB)
hdfs_supervised_scores_v2.csv (404,179 rows)
Test: F1=0.252, P=0.426, R=0.179
```

### 3.2 Runtime Inference Flow

```
Client POST /ingest
  {timestamp, service, session_id, token_id, label}
        |
        | AuthMiddleware (X-API-Key validation)
        | MetricsMiddleware (latency tracking)
        v
routes.py: ingest_event()
        |
        v
Pipeline.process_event(event)
        |
        v
InferenceEngine.ingest(event)
        |
        | SequenceBuffer.push(stream_key, token_id)
        | stream_key = f"{service}:{session_id}" (default)
        |
        | Window NOT yet full -> return None (no scoring)
        | Window full (window_size events) OR stride interval reached
        v
Score window (mode-dependent):
  baseline:    BaselineFeatureExtractor -> IsolationForest.score_samples()
  transformer: AnomalyScorer -> NextTokenTransformerModel log-likelihood
  ensemble:    (b_score/thr_b + t_score/thr_t) / 2
  demo_mode:   Returns fallback_score (default 2.0) directly
        |
        v
RiskResult {stream_key, timestamp, model, risk_score, is_anomaly, threshold,
            evidence_window, top_predictions, meta}
        |
        v
AlertManager.emit(risk_result)
        |
        | If is_anomaly AND not in cooldown for this stream_key:
        |   Classify severity: critical(1.5x) / high(1.2x) / medium(1.0x) / low
        |   Create Alert {alert_id, severity, service, score, timestamp, ...}
        |   Record cooldown timestamp
        |   Append to ring buffer (deque maxlen=200)
        |   N8nWebhookClient.post(alert) or write to artifacts/n8n_outbox/
        v
IngestResponse {window_emitted, risk_result, alert}
        |
        v
HTTP 200 to client
```

---

## 4. Repository Structure

```
predictive-log-anomaly-engine/
|
+-- src/                     # Application source (runtime + API + models)
|   +-- api/                 # FastAPI application
|   +-- runtime/             # Streaming inference engine
|   +-- modeling/            # ML model wrappers
|   +-- alerts/              # Alerting system
|   +-- health/              # Health checks
|   +-- security/            # Authentication
|   +-- observability/       # Metrics and logging
|   +-- data/                # Data models and synthetic generation
|   +-- parsing/             # Template mining and tokenization
|   +-- sequencing/          # Sequence building
|
+-- ai_workspace/            # Offline analysis pipeline (Stages 21-26)
|   +-- stage_22_template_mining/
|   +-- stage_23_sequence_builder/
|   +-- stage_24_baseline_model/
|   +-- stage_25_evaluation/
|   +-- stage_26_hdfs_supervised/
|   +-- reports/             # Stage-level experiment reports
|   +-- logs/                # Execution logs per stage
|
+-- scripts/                 # Numbered execution scripts (Stages 1-7)
+-- tests/                   # pytest test suite (233 total, 211 fast)
|   +-- unit/                # Unit tests
|   +-- integration/         # API integration tests
|
+-- templates/               # Web UI (index.html)
+-- prometheus/              # Prometheus config
+-- grafana/                 # Grafana provisioning + dashboards
+-- docs/                    # Project documentation
+-- data/                    # Datasets and intermediate artifacts
+-- models/                  # Runtime model artifacts (loaded at startup)
+-- artifacts/               # Alert outputs, n8n outbox
+-- .github/workflows/       # CI/CD pipeline definition
+-- Dockerfile               # Container image
+-- docker-compose.yml       # Multi-service orchestration
```

---

## 5. Stage Pipeline Explanation

### Stage 21 — Data Sampling
Samples 1 million events from the full 15.9M-row dataset using stratified selection to preserve
label and dataset distribution. Produces the working sample used by all downstream stages.

### Stage 22 — Template Mining
Applies a 9-step regex substitution pipeline to normalize log messages into templates:
`BLK -> HEX numbers -> IP addresses -> dates -> node IDs -> paths -> hex values -> numbers -> whitespace`.
Produces 7,833 unique templates. BGL contributes 7,792; HDFS uses 41. Template IDs are alphabetically
assigned rank integers for stability.

### Stage 23 — Sequence Building
Groups events by `session_id` and builds fixed-length feature vectors per session:
- 7 meta features (event count, unique templates, anomaly rate, entropy, etc.)
- 100 top template ID raw counts
- 100 top template ID normalized frequencies
- 100 top bigram raw counts (template transition pairs)
- 100 top bigram normalized frequencies

V2 adds unique ratio, template entropy, and bigram features over V1's simpler 204-feature set.

### Stage 24 — Baseline Model
Trains an Isolation Forest (n_estimators=300) on the 407-feature session vectors.
Uses an F1-optimal threshold scan over 300 candidates between the 1st and 99th percentiles of the
score distribution. V2 achieves BGL F1=0.965 (near-perfect) but HDFS F1=0.047 (unsupervised
methods struggle with the low 2.35% anomaly rate in HDFS).

### Stage 25 — Evaluation
Evaluates the baseline model on the held-out test split. Generates ROC curves, PR curves,
score histograms, and confusion matrices (per-dataset and overall). The weak HDFS performance
motivates Stage 26.

### Stage 26 — Supervised HDFS Model
Trains a Logistic Regression (L2) classifier specifically on HDFS session features where the
baseline model fails. Achieves PR-AUC=0.2334 vs HGBC PR-AUC=0.1845. Best F1 threshold=0.71259
gives Test F1=0.252 (P=0.426, R=0.179) - significantly better than the unsupervised baseline
for HDFS.

### Stage 5 — Runtime Inference
Implements the streaming inference engine used by the API. Maintains a `SequenceBuffer` per
`stream_key` (service:session_id pair) with LRU eviction. Supports three modes:
- **baseline**: Feature extraction + IsolationForest scoring
- **transformer**: Next-token log-likelihood scoring
- **ensemble**: Normalized combination of both

### Stage 6 — Alerting
`AlertManager` wraps `InferenceEngine` output with:
- Per-stream cooldown deduplication
- Severity classification (critical/high/medium/low)
- N8n webhook integration (DRY_RUN writes to `artifacts/n8n_outbox/`)

### Stage 7 — REST API
Production-grade FastAPI application with:
- `POST /ingest` — tokenized event ingestion with full pipeline execution
- `GET /alerts` — ring buffer query
- `GET /health` — readiness/liveness probe
- `GET /metrics` — Prometheus text format
- `GET /` — single-page demo UI
- `POST /query` — RAG stub with keyword-based KB retrieval
- API Key authentication (X-API-Key header)
- Prometheus metrics middleware

### Stage 7.1 — Demo UI
Vanilla JavaScript single-page app served from `templates/index.html`.
Three tabs: manual event ingestion, alert viewer with auto-refresh, and RAG question answering.

### Stage 8 — Docker + CI/CD + Observability
Full containerization with `docker-compose.yml` (api + prometheus + grafana).
GitHub Actions CI with lint, fast test suite (211 tests), security scanning (pip-audit + trivy),
and Docker smoke test (build + ingest + alert verification).

---

## 6. Diagram References

| Diagram | Location |
|---------|----------|
| Grafana dashboard JSON | `grafana/dashboards/stage08_api_observability.json` |
| Prometheus scrape config | `prometheus/prometheus.yml` |
| CI/CD workflow | `.github/workflows/ci.yml` |
| Architecture reports | `ai_workspace/reports/` |

The `docs/diagrams/` directory exists for future diagram assets (architecture diagrams, data flow
charts). No rendered diagrams are currently committed; the Grafana dashboard is the primary
visual representation of runtime system behavior.

---

## 7. Architectural Strengths

### Separation of Concerns
Each pipeline stage is independently executable with its own script, log file, and report.
The `src/` package hierarchy mirrors the stage structure, making it straightforward to trace
any behavior back to its implementation.

### Multiple Scoring Modes
The three-mode scoring architecture (baseline/transformer/ensemble) allows the system to operate
even when model artifacts are unavailable (demo mode with synthetic scores), making CI/CD and
testing work without production model files.

### Comprehensive Observability
Prometheus metrics cover every critical code path: event ingestion, window emission, alert firing
(by severity), and latency histograms for both ingest and scoring operations. Pre-built Grafana
dashboards allow immediate visualization without manual panel configuration.

### Fast Test Suite
The `pytest.mark.slow` / `pytest.mark.integration` marker system allows 211 tests to run in ~12
seconds on any machine without model artifacts. This enables rapid iteration and reliable CI.

### Demo Readiness
The `DEMO_MODE=true` environment flag enables a fully functional demonstration without trained
model files. The warmup task automatically pre-fills the alert buffer for immediate visual feedback.

### Configuration-Driven Behavior
All operational parameters (window size, stride, cooldown, scoring thresholds, demo mode) are
controlled via environment variables with sensible defaults, following 12-factor app principles.

---

## 8. Known Limitations

### Model Performance on HDFS
The unsupervised Isolation Forest achieves near-perfect performance on BGL (F1=0.965) but
struggles significantly with HDFS (F1=0.047). The supervised LogReg-L2 improves HDFS to F1=0.252,
but neither model meets production-grade recall requirements for HDFS anomalies.

### Offline-Only Training Pipeline
The Stages 21-26 pipeline runs offline as batch scripts. There is no automated re-training trigger,
online learning, or model versioning system. Model artifacts must be manually produced and placed
in the `models/` directory.

### Single-Node Architecture
The system is designed for single-node deployment. SequenceBuffer uses in-process LRU eviction
without distributed state. High-volume multi-instance deployments would require external state
(Redis, etc.) for the sequence buffer.

### Narrow Score Distribution
The IsolationForest produces scores in a narrow range ([0.297, 0.443]), which makes threshold
selection sensitive and reduces the gap between normal and anomalous scores for HDFS sessions.

### Template Vocabulary Fixed at Training Time
The template miner's regex vocabulary is fixed at training time. Novel log patterns not seen
during Stage 22 template mining will be mapped to the catch-all template, potentially reducing
detection accuracy on unseen log sources.

### Transformer Token Sequence Mismatch
Demo-mode models were trained on 2-3 token sequences, but the runtime window emits 50-token
windows, causing score inflation (~0.54 >> threshold 0.33). Production use requires retraining
with windows matching the runtime configuration.
