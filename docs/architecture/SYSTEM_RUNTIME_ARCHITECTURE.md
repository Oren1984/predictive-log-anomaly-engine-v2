# System Runtime Architecture

**Project:** Predictive Log Anomaly Engine v2
**Document scope:** Full runtime architecture — data flow, model pipeline, API layer, alert system, and deployment topology.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [V1 Pipeline Architecture](#2-v1-pipeline-architecture)
3. [V2 AI Pipeline Architecture](#3-v2-ai-pipeline-architecture)
4. [Training Pipeline](#4-training-pipeline)
5. [Inference Pipeline](#5-inference-pipeline)
6. [API Layer](#6-api-layer)
7. [Alert System](#7-alert-system)
8. [Deployment Architecture](#8-deployment-architecture)

---

## 1. System Overview

The Predictive Log Anomaly Engine ingests raw log streams in real time, scores behavioral anomalies using machine learning, assigns severity levels, and fires structured alerts — all before a full service failure occurs.

Two inference pipelines run in parallel behind a single FastAPI service, controlled by the `MODEL_MODE` environment variable:

| Pipeline | Class | Algorithm | Input form |
|----------|-------|-----------|------------|
| **V1** | `InferenceEngine` | IsolationForest / Transformer | Pre-tokenized event dict |
| **V2** | `V2Pipeline` | Word2Vec + LSTM + Autoencoder + MLP | Raw log string |

```
                       ┌──────────────────────────────────────────────────────┐
                       │                  FastAPI Service                     │
                       │                                                      │
  Raw log strings ────▶│  POST /v2/ingest ──▶ V2Pipeline ──▶ Alert System   │
  Token-id events ────▶│  POST /ingest    ──▶ InferenceEngine ──▶ Alert Sys │
                       │                                                      │
                       │  GET  /v2/alerts  ◀── Ring buffer (200 slots)       │
                       │  GET  /alerts     ◀── Ring buffer (200 slots)       │
                       │  GET  /health                                        │
                       │  GET  /metrics    ──▶ Prometheus scrape             │
                       └──────────────────────────────────────────────────────┘
                                                  │
                                    ┌─────────────┴────────────┐
                                    ▼                          ▼
                              Prometheus                    Grafana
                           (time-series DB)             (dashboards)
```

All models and vocabulary artifacts are loaded once at startup and held in memory. No database is required for inference.

---

## 2. V1 Pipeline Architecture

The V1 pipeline (`src/runtime/inference_engine.py`) is a **sequence-based anomaly scorer** built on classical ML. It operates on pre-tokenized event streams where each event already carries a `token_id` (template identifier).

### 2.1 Components

```
Incoming event dict
  {service, session_id, token_id, timestamp}
          │
          ▼
  ┌─────────────────────────────────────────────────────────┐
  │                    SequenceBuffer                       │
  │  Per-stream deque  (keyed by "service:session_id")      │
  │  window_size = 50 (default) │ stride = 10 (default)    │
  │                                                         │
  │  Emits a Sequence when:                                 │
  │    n_events >= window_size                              │
  │    AND (n_events - window_size) % stride == 0           │
  └────────────────────────┬────────────────────────────────┘
                           │  Sequence {tokens[], timestamps[], label}
                           ▼
          ┌────────────────────────────────┐
          │      Scoring (mode-based)      │
          ├────────────────────────────────┤
          │  baseline   IsolationForest    │
          │  transformer  NLL scorer       │
          │  ensemble   normalized average │
          └────────────────────────────────┘
                           │  risk_score (float)
                           ▼
                  Threshold comparison
                  is_anomaly = score >= threshold
                           │
                           ▼
                       RiskResult
```

### 2.2 Baseline Model — IsolationForest

**Feature extraction** (`BaselineFeatureExtractor`):

| Feature | Description |
|---------|-------------|
| `sequence_length` | Number of tokens in the window |
| `unique_count` | Distinct token IDs |
| `unique_ratio` | `unique_count / sequence_length` |
| `template_entropy` | Shannon entropy over token distribution |
| `tid_raw_{tid}` | Raw count per top-K (default 100) token |
| `tid_norm_{tid}` | Normalized count per top-K token |

**Model** (`BaselineAnomalyModel`):

- Algorithm: `sklearn.ensemble.IsolationForest`
- Hyperparameters: `n_estimators=300`, `random_state=42`
- Score convention: higher score = more anomalous (negated from sklearn internals)
- Default threshold: `0.33`
- Artifact path: `models/baseline.pkl`

### 2.3 Transformer Model

- Architecture: `NextTokenTransformerModel` — next-token prediction
- Scorer: `AnomalyScorer` — measures negative log-likelihood (NLL) of the observed token sequence
- Higher NLL = sequence is unexpected = anomalous
- Default threshold: `0.034`
- Artifact path: `models/transformer.pt`

### 2.4 Ensemble Mode

Scores from both models are normalized relative to their own thresholds and averaged:

```
b_norm = baseline_score  / threshold_baseline
t_norm = transformer_score / threshold_transformer
ensemble_score = (b_norm + t_norm) / 2.0
```

Threshold for ensemble is `1.0` — i.e., the session is anomalous if the average normalized score exceeds `1.0` (either model "votes" anomalous on average).

### 2.5 RiskResult

```python
@dataclass
class RiskResult:
    stream_key:     str           # "service:session_id"
    timestamp:      float | str   # wall-clock time of last event
    model:          str           # "baseline" | "transformer" | "ensemble"
    risk_score:     float         # anomaly score
    is_anomaly:     bool          # score >= threshold
    threshold:      float         # decision threshold used
    evidence_window: dict         # tokens, template snippets, timestamps
    top_predictions: list | None  # transformer only
    meta:           dict
```

### 2.6 Artifact dependencies

```
artifacts/
  vocab.json                 # str(token_id) → template_text
  templates.json             # str(template_id) → template_text
  threshold.json             # {"threshold": 0.33}
  threshold_transformer.json # {"threshold": 0.034}
  threshold_runtime.json     # optional runtime overrides
models/
  baseline.pkl               # fitted IsolationForest
  transformer.pt             # NextTokenTransformerModel weights
```

---

## 3. V2 AI Pipeline Architecture

The V2 pipeline (`src/runtime/pipeline_v2.py`) is a **four-stage deep learning pipeline** that operates on raw log strings. It requires no pre-tokenization from the caller.

### 3.1 End-to-end data flow

```
raw log string
      │
      ▼
┌───────────────────────────────────────────────────────┐
│  Stage 1 — _V2LogTokenizer                           │
│                                                       │
│  1. Apply 9 regex substitutions (TemplateMiner-       │
│     compatible):                                      │
│       blk_-?\d+  →  <BLK>                            │
│       timestamp patterns  →  <TS>                    │
│       IP addresses  →  <IP>                          │
│       date patterns  →  <DATE>                       │
│       rack/node IDs  →  <NODE>                       │
│       file paths  →  <PATH>                          │
│       hex literals  →  <HEX>                         │
│       numeric literals  →  <NUM>                     │
│       whitespace collapse  →  single space           │
│  2. Lookup normalized string in templates.csv         │
│     → template_id   (UNK_ID=1 if absent)             │
│  3. token_id = template_id + 2                       │
│     (PAD=0, UNK=1, first real template = 2)          │
└──────────────────────┬────────────────────────────────┘
                       │  token_id (int)
                       ▼
┌───────────────────────────────────────────────────────┐
│  Stage 2 — Word2Vec Embedding                        │
│                                                       │
│  wv[str(token_id)] → float32[vec_dim=100]            │
│  OOV → zero vector float32[100]                      │
│                                                       │
│  Rolling window buffer (per stream_key):             │
│    deque(maxlen=window_size=10)                      │
│    Waits until full before emitting                  │
└──────────────────────┬────────────────────────────────┘
                       │  window tensor [1, 10, 100]
                       ▼
┌───────────────────────────────────────────────────────┐
│  Stage 3 — SystemBehaviorModel (LSTM)                │
│                                                       │
│  Input:   [batch=1, seq_len=10, input_dim=100]       │
│  Architecture:                                        │
│    Stacked LSTM (num_layers=2, hidden_dim=128)       │
│    dropout=0.2 between layers                        │
│    Last hidden state → Linear → [batch, 128]         │
│  Output:  context vector [1, hidden_dim=128]         │
└──────────────────────┬────────────────────────────────┘
                       │  context [1, 128]
                       ▼
┌───────────────────────────────────────────────────────┐
│  Stage 4 — AnomalyDetector (Denoising Autoencoder)   │
│                                                       │
│  Encoder:                                             │
│    Linear(128 → 64) → ReLU → Dropout(0.1)           │
│    Linear(64  → 32) → latent                         │
│  Decoder:                                             │
│    Linear(32  → 64) → ReLU → Dropout(0.1)           │
│    Linear(64  → 128) → reconstruction                │
│  Score:                                               │
│    error = MSE(input, reconstruction) per sample     │
│    is_anomaly = error > calibrated_threshold         │
│  Outputs:                                             │
│    AEOutput.latent         [1, latent_dim=32]        │
│    AEOutput.reconstructed  [1, 128]                  │
│    AEOutput.error          [1]  ← anomaly score      │
└──────────────────────┬────────────────────────────────┘
                       │  latent [1,32] + error [1]
                       ▼
┌───────────────────────────────────────────────────────┐
│  Stage 5 — SeverityClassifier (MLP)                  │
│                                                       │
│  Input:  concat(latent, error) → [1, 33]             │
│  Architecture:                                        │
│    Linear(33 → 64) → ReLU → Dropout(0.3)            │
│    Linear(64 → 64) → ReLU → Dropout(0.3)            │
│    Linear(64 →  3) → softmax                         │
│  Classes: 0=info  1=warning  2=critical              │
│  Output:                                              │
│    SeverityOutput.label          "info|warning|..."  │
│    SeverityOutput.confidence     float 0–1           │
│    SeverityOutput.probabilities  [p_info, p_w, p_c]  │
└──────────────────────┬────────────────────────────────┘
                       │
                       ▼
                   V2Result
```

### 3.2 V2Result

```python
@dataclass
class V2Result:
    window_emitted:         bool
    stream_key:             str             # "<service>/<session_id>"
    anomaly_score:          float | None    # AE reconstruction error
    is_anomaly:             bool  | None    # score > threshold
    severity:               str   | None    # "info" | "warning" | "critical"
    severity_confidence:    float | None    # softmax probability 0–1
    severity_probabilities: list  | None    # [p_info, p_warning, p_critical]
```

`window_emitted=False` is returned for every call while the rolling buffer is still filling. This is by design — the caller always receives a result, but should only act on results where `window_emitted=True`.

### 3.3 Template vocabulary

The templates vocabulary lives in `data/intermediate/templates.csv` and is generated offline by DrainParser-style template mining over the raw log corpus. At inference time, `_V2LogTokenizer` loads this file once and holds a `dict[template_text → template_id]` in memory.

```
data/intermediate/templates.csv
  template_id   template_text                                  count   anomaly_rate
  0             INFO dfs.DataNode$DataXceiver: Receiving ...   44302   0.01
  1             INFO dfs.FSNamesystem.audit: allowed=true ...  12000   0.00
  ...
  7832          WARN dfs.FSNamesystem: ...                     3       0.88
```

### 3.4 Artifact dependencies

```
models/
  embeddings/word2vec.model          # gensim Word2Vec (7840-word vocab)
  behavior/behavior_model.pt         # SystemBehaviorModel weights + config
  anomaly/anomaly_detector.pt        # AnomalyDetector weights + calibrated threshold
  severity/severity_classifier.pt    # SeverityClassifier weights + config
data/intermediate/
  templates.csv                      # 7833-template vocabulary
```

---

## 4. Training Pipeline

V2 models are trained offline in four sequential stages. Each stage depends on the artifacts produced by the previous one.

```
data/processed/sequences_train.parquet   ─┐
data/processed/events_tokenized.parquet  ─┤─▶  Stage 1: Embeddings
data/intermediate/templates.csv          ─┘
                                                     │
                                          models/embeddings/word2vec.model
                                                     │
                                                     ▼
                                         Stage 2: Behavior Model
                                                     │
                                          models/behavior/behavior_model.pt
                                                     │
                                                     ▼
                                         Stage 3: Autoencoder
                                                     │
                                          models/anomaly/anomaly_detector.pt
                                                     │
                                                     ▼
                                         Stage 4: Severity Classifier
                                                     │
                                          models/severity/severity_classifier.pt
```

### 4.1 Stage 1 — Word2Vec Embeddings

**Script:** `python -m training.train_embeddings`

The Word2Vec model treats every token_id as a "word". Sentences are built from three data sources to maximize vocabulary coverage:

| Source | Description | Sentences |
|--------|-------------|-----------|
| `sequences_train.parquet` `tokens` column | 1,600 real labeled session sequences, lengths 12–42 | 1,600 |
| `events_tokenized.parquet` session groups | All sessions with ≥ 3 events — real co-occurrence data across all templates | ~130,582 |
| `templates.csv` text tokenization | Templates grouped by first 4 non-placeholder words → semantic neighborhood sentences | ~72 |

Key hyperparameters:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `vec_dim` | 100 | Embedding dimensionality |
| `window` | 5 | Context window size |
| `min_count` | 1 | Include all 7,833 templates (no pruning) |
| `epochs` | 10 | Training passes over corpus |
| `workers` | 4 | Parallel gensim workers |

**Result:** 7,840-word vocabulary, 100% template coverage, 0 OOV at inference.

### 4.2 Stage 2 — Behavior Model (LSTM)

**Script:** `python -m training.train_behavior_model`

Trains the LSTM to produce a fixed-length context vector from a window of embeddings. Training sequences come from `sequences_train.parquet`.

| Hyperparameter | Value |
|----------------|-------|
| `input_dim` | 100 (embedding size) |
| `hidden_dim` | 128 |
| `num_layers` | 2 |
| `dropout` | 0.2 |
| `window_size` | 10 |

### 4.3 Stage 3 — Autoencoder (Anomaly Detector)

**Script:** `python -m training.train_autoencoder`

Trains a denoising autoencoder to reconstruct normal behavior. Only sessions with `label=0` (normal) are used for training, so the model learns the expected reconstruction error for healthy sequences. Anomalous sessions will produce higher-than-expected errors at inference.

| Hyperparameter | Value |
|----------------|-------|
| `input_dim` | 128 (LSTM hidden dim) |
| `latent_dim` | 32 |
| `intermediate_dim` | 64 |
| `noise_std` | 0.05 |
| `dropout` | 0.1 |

The anomaly threshold is calibrated post-training at a high percentile of the normal-session error distribution. The calibrated threshold is saved inside the model checkpoint (`anomaly_detector.pt`).

### 4.4 Stage 4 — Severity Classifier (MLP)

**Script:** `python -m training.train_severity_model`

Runs the full pipeline (Word2Vec → LSTM → AE) over the training sequences to produce `(latent_vector, anomaly_score)` pairs, then assigns bootstrap severity labels by score percentile:

```
score < p33           →  0 (info)
p33 ≤ score < p66     →  1 (warning)
score ≥ p66           →  2 (critical)
```

The MLP is then trained on `concat(latent_vector, anomaly_score)` → `severity_class`.

| Hyperparameter | Value |
|----------------|-------|
| `input_dim` | 33 (latent_dim=32 + score=1) |
| `hidden_dim` | 64 |
| `num_classes` | 3 |
| `dropout` | 0.3 |
| `epochs` | 30 |

Training command (all four stages in order):

```bash
python -m training.train_embeddings
python -m training.train_behavior_model
python -m training.train_autoencoder
python -m training.train_severity_model
```

---

## 5. Inference Pipeline

End-to-end flow for a single raw log event through the V2 pipeline:

```
┌──────────────────────────────────────────────────────────────────────┐
│  CLIENT  POST /v2/ingest                                            │
│  {                                                                   │
│    "raw_log":    "081109 204621 34 INFO dfs.DataNode...",           │
│    "service":    "hdfs",                                            │
│    "session_id": "blk_-1608999687919862906",                        │
│    "timestamp":  1257817581.0                                       │
│  }                                                                   │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  _V2LogTokenizer │
                    │                  │
                    │  generalize()    │
                    │    9 regex subs  │
                    │  → template_text │
                    │                  │
                    │  lookup in       │
                    │  templates.csv   │
                    │  → template_id   │
                    │                  │
                    │  token_id =      │
                    │  template_id + 2 │
                    └────────┬─────────┘
                             │  token_id = 42
                             ▼
                    ┌──────────────────┐
                    │  Word2Vec wv     │
                    │                  │
                    │  wv["42"]        │
                    │  → float32[100]  │
                    │  (zero if OOV)   │
                    └────────┬─────────┘
                             │  embedding [100]
                             ▼
              ┌──────────────────────────────┐
              │  Rolling Window Buffer        │
              │                              │
              │  deque(maxlen=10)            │
              │  keyed by "hdfs/blk_..."     │
              │                              │
              │  len < 10  →  return early   │
              │  (window_emitted=False)      │
              │                              │
              │  len == 10  →  continue      │
              └──────────────┬───────────────┘
                             │  window [1, 10, 100]
                             ▼
                    ┌──────────────────┐
                    │  LSTM Behavior   │
                    │  Model           │
                    │                  │
                    │  2-layer LSTM    │
                    │  hidden_dim=128  │
                    │  → context       │
                    │  [1, 128]        │
                    └────────┬─────────┘
                             │  context [1, 128]
                             ▼
                    ┌──────────────────┐
                    │  Denoising       │
                    │  Autoencoder     │
                    │                  │
                    │  encode → [1,32] │
                    │  decode → [1,128]│
                    │  error = MSE     │
                    │                  │
                    │  is_anomaly =    │
                    │  error > thr     │
                    └────────┬─────────┘
                             │  latent [1,32] + error
                             ▼
                    ┌──────────────────┐
                    │  Severity MLP    │
                    │                  │
                    │  [1,33] → [1,3]  │
                    │  softmax         │
                    │  → "critical"    │
                    │    confidence    │
                    └────────┬─────────┘
                             │  V2Result
                             ▼
                  ┌──────────────────────┐
                  │  AlertManager        │
                  │                      │
                  │  if is_anomaly:      │
                  │    cooldown check    │
                  │    → maybe fire      │
                  │      Alert           │
                  │    push to ring buf  │
                  └──────────┬───────────┘
                             │  IngestV2Response
                             ▼
                          CLIENT
```

### 5.1 Window accumulation semantics

Each call to `process_log()` always returns a `V2Result`. Callers should check `window_emitted` before interpreting `anomaly_score`, `is_anomaly`, or `severity` — those fields are `None` when the window is still filling.

```
Call 1:  window_emitted=False  (buffer: 1/10)
Call 2:  window_emitted=False  (buffer: 2/10)
...
Call 10: window_emitted=True   (buffer: 10/10) ← scores computed here
Call 11: window_emitted=True   (buffer slides: drops oldest, adds newest)
Call 12: window_emitted=True   (scores computed on every new event)
```

### 5.2 Per-stream isolation

Each unique `(service, session_id)` pair gets its own independent `deque`. Streams do not share state. The buffer dictionary is held in `V2Pipeline._buffers` and grows incrementally as new streams are seen.

```
_buffers = {
    "hdfs/blk_-1608999687919862906":  deque([e1, e2, ..., e10], maxlen=10),
    "hdfs/blk_7503483334202473044":   deque([e1, e2], maxlen=10),
    "bgl/job_001":                    deque([e1, ..., e7], maxlen=10),
    ...
}
```

---

## 6. API Layer

### 6.1 Application structure

```
src/api/
  app.py        # FastAPI factory, lifespan (model loading + warmup)
  routes.py     # V1 endpoints (/ingest, /alerts, /health, /metrics)
  routes_v2.py  # V2 endpoints (/v2/ingest, /v2/alerts)
  schemas.py    # Pydantic request/response models
  pipeline.py   # PipelineContainer (engine + alert manager + ring buffer)
  settings.py   # Environment-driven configuration (AppSettings)
```

The application is created by `create_app()` (factory pattern for testability). At startup, the FastAPI lifespan handler loads all model artifacts; at shutdown, resources are released.

### 6.2 V2 endpoints

#### `POST /v2/ingest`

Accepts a raw log string and routes it through the V2 pipeline.

**Request** (`IngestV2Request`):

```json
{
  "raw_log":    "081109 204621 34 INFO dfs.DataNode$DataXceiver: ...",
  "service":    "hdfs",
  "session_id": "blk_-1608999687919862906",
  "timestamp":  1257817581.0
}
```

**Response** (`IngestV2Response`):

```json
{
  "window_emitted": true,
  "result": {
    "stream_key":             "hdfs/blk_-1608999687919862906",
    "anomaly_score":          0.017976,
    "is_anomaly":             true,
    "severity":               "critical",
    "severity_confidence":    0.9995,
    "severity_probabilities": [0.0001, 0.0004, 0.9995]
  },
  "alert": {
    "alert_id":   "a3f2c1d4-...",
    "severity":   "critical",
    "service":    "hdfs",
    "score":      0.017976,
    "timestamp":  1257817581.0
  }
}
```

#### `GET /v2/alerts`

Returns recent alerts from the ring buffer, newest first.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Maximum alerts to return |

**Response** (`AlertListV2Response`):

```json
{
  "count": 3,
  "alerts": [
    { "alert_id": "...", "severity": "critical", "score": 0.018, ... },
    ...
  ]
}
```

### 6.3 V1 endpoints

#### `POST /ingest`

Accepts a pre-tokenized log event dict.

**Request** (`IngestRequest`):

```json
{
  "timestamp":  1257817581.0,
  "service":    "hdfs",
  "session_id": "blk_-1608999687919862906",
  "token_id":   5413,
  "label":      null
}
```

**Response** (`IngestResponse`):

```json
{
  "window_emitted": true,
  "risk_result": {
    "stream_key":  "hdfs:blk_-1608999687919862906",
    "model":       "baseline",
    "risk_score":  0.42,
    "is_anomaly":  true,
    "threshold":   0.33
  },
  "alert": { ... }
}
```

#### `GET /alerts`

Same semantics as `/v2/alerts` but returns V1 alert objects.

### 6.4 Shared endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness/readiness probe. Returns `status`, `uptime_seconds`, `components` dict with per-model health. Health gauge values: `1.0` = healthy, `0.5` = degraded. |
| `/metrics` | GET | Prometheus text-format metrics scraped by the sidecar container. |

### 6.5 Authentication

An API key middleware is active unless `DISABLE_AUTH=true`. Public endpoints (configurable via `PUBLIC_ENDPOINTS` env var) bypass auth:

```
/health, /metrics, /, /query  (defaults)
```

---

## 7. Alert System

### 7.1 Architecture

```
V2Result / RiskResult
        │
        ▼
┌───────────────────────────────────────────────────────┐
│  AlertManager  (src/alerts/manager.py)               │
│                                                       │
│  emit(result):                                        │
│    1. is_anomaly=False?  →  return []  (no alert)    │
│    2. score < policy.threshold?  →  return []        │
│    3. same stream_key alerted within cooldown?        │
│          →  return []  (suppressed)                  │
│    4. determine severity bucket                       │
│    5. build Alert                                     │
│    6. update _last_alert[stream_key] = now()          │
│    7. return [Alert]                                  │
└──────────────────────┬────────────────────────────────┘
                       │  Alert
                       ▼
┌───────────────────────────────────────────────────────┐
│  Ring Buffer  (deque, maxlen=200)                    │
│                                                       │
│  Newest alerts at front.                             │
│  When full, oldest alert is silently evicted.        │
│  GET /v2/alerts retrieves from this buffer.          │
└───────────────────────────────────────────────────────┘
```

### 7.2 Alert model

```python
@dataclass
class Alert:
    alert_id:        str     # UUID
    severity:        str     # "critical" | "high" | "medium" | "low"
    service:         str
    score:           float   # raw anomaly score
    timestamp:       float   # wall-clock epoch
    evidence_window: dict    # templates_preview, token_count, start/end timestamps
    model_name:      str
    threshold:       float
    meta:            dict
```

### 7.3 AlertPolicy

```python
@dataclass
class AlertPolicy:
    threshold:                    float = 0.0    # additional min-score gate
    cooldown_seconds:             float = 60.0   # per-stream quiet period
    aggregation_window_seconds:   float = 300.0  # metadata only
    min_events:                   int   = 0

    severity_buckets: dict = {
        "critical": 1.5,   # score >= 1.5 × model_threshold
        "high":     1.2,   # score >= 1.2 × model_threshold
        "medium":   1.0,   # score >= 1.0 × model_threshold
        # fallback → "low"
    }
```

### 7.4 Cooldown mechanism

The cooldown prevents alert floods from a single misbehaving stream. Each fired alert records the wall-clock time against the stream key. Any subsequent result from the same stream within `cooldown_seconds` is suppressed:

```
Stream "hdfs/blk_A"  fires alert at  T=0s
                     result at        T=30s  → suppressed (30 < 60)
                     result at        T=70s  → alert fired (70 > 60)
```

The Docker compose default is `ALERT_COOLDOWN_SECONDS=0` (disabled for demo purposes). In production the recommended value is `60`.

### 7.5 Ring buffer

The ring buffer is a `collections.deque(maxlen=200)` held in memory by the `InferenceEngineV2` / `PipelineContainer` instance. Default capacity is 200 slots, configurable via `ALERT_BUFFER_SIZE`. When the buffer is full and a new alert arrives, the oldest alert is evicted automatically. The buffer is not persisted to disk; a service restart clears it.

### 7.6 Severity bucketing

Severity is assigned by comparing the raw anomaly score against multiples of the model's decision threshold:

```
score / threshold:
  ≥ 1.5  →  critical
  ≥ 1.2  →  high
  ≥ 1.0  →  medium
  < 1.0  →  low   (only reaches here if policy.threshold=0)
```

---

## 8. Deployment Architecture

### 8.1 Container topology

```
┌──────────────────────────────────────────────────────────────────┐
│  Docker Compose Network                                         │
│                                                                  │
│  ┌─────────────────────────────┐                                │
│  │  api  (custom image)        │◀──── POST /v2/ingest          │
│  │  Port 8000:8000             │                                 │
│  │  FastAPI + Uvicorn          │──── GET /metrics ──────────┐  │
│  │                             │                             │  │
│  │  MODEL_MODE=baseline        │                             │  │
│  │  DEMO_MODE=true             │                             │  │
│  │  WINDOW_SIZE=5              │                             │  │
│  │  STRIDE=1                   │                             │  │
│  │  ALERT_COOLDOWN_SECONDS=0   │                             │  │
│  └─────────────────────────────┘                             │  │
│                                                               │  │
│  ┌─────────────────────────────┐                             │  │
│  │  prometheus                 │◀────────────────────────────┘  │
│  │  prom/prometheus:v2.51.0    │                                 │
│  │  Port 9090:9090             │                                 │
│  └────────────┬────────────────┘                                │
│               │                                                  │
│  ┌────────────▼────────────────┐                                │
│  │  grafana                    │                                 │
│  │  grafana/grafana:10.4.2     │                                 │
│  │  Port 3000:3000             │                                 │
│  │  GF_ADMIN_PASSWORD=admin    │                                 │
│  └─────────────────────────────┘                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 FastAPI / Uvicorn

The API server is started via:

```bash
uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

The `--factory` flag instructs Uvicorn to call `create_app()` to obtain the ASGI application, enabling the lifespan context manager for clean model loading and resource teardown.

Container health is checked by Docker at startup:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### 8.3 Environment configuration

All runtime behaviour is driven by environment variables, making the container config-injectable without rebuilding:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_MODE` | `ensemble` | Active pipeline: `v1`, `v2`, or `ensemble` |
| `WINDOW_SIZE` | `50` | Rolling window length (V1 default) |
| `STRIDE` | `10` | V1 emit interval |
| `ALERT_BUFFER_SIZE` | `200` | Ring buffer capacity |
| `ALERT_COOLDOWN_SECONDS` | `60.0` | Per-stream alert quiet period |
| `DEMO_MODE` | `false` | Enable synthetic fallback scores |
| `DEMO_SCORE` | `2.0` | Fallback score value in demo mode |
| `DEMO_WARMUP_ENABLED` | `false` | Auto-inject warmup events on startup |
| `DEMO_WARMUP_EVENTS` | `75` | Number of warmup events to inject |
| `DISABLE_AUTH` | `false` | Bypass API key check |
| `API_KEY` | — | Bearer token for authenticated endpoints |
| `PUBLIC_ENDPOINTS` | `/health,/metrics,/,/query` | Auth-exempt paths |
| `METRICS_ENABLED` | `true` | Expose Prometheus `/metrics` endpoint |

### 8.4 Prometheus metrics

Metrics are exposed at `GET /metrics` in Prometheus text format. The Prometheus container is pre-configured to scrape this endpoint.

| Metric | Type | Description |
|--------|------|-------------|
| `ingest_events_total` | Counter | Total events received at `/ingest` |
| `ingest_windows_total` | Counter | Windows emitted by InferenceEngine |
| `alerts_total` | Counter | Alerts fired, labelled by `severity` |
| `ingest_errors_total` | Counter | Unhandled errors during ingest |
| `ingest_latency_seconds` | Histogram | End-to-end `/ingest` handler latency |
| `scoring_latency_seconds` | Histogram | Model scoring latency per emitted window |
| `service_health` | Gauge | `1.0` healthy · `0.5` degraded · `0.0` unhealthy |

Histogram buckets: `(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)` seconds.

### 8.5 Grafana

Grafana is provisioned with pre-built dashboards for:

- Ingest throughput and error rates
- Alert volume by severity over time
- Model scoring latency (p50 / p95 / p99)
- Service health gauge

Default login: `admin` / `admin`. Datasource is auto-provisioned pointing at `http://prometheus:9090`.

### 8.6 Production override

A `docker-compose.prod.yml` override is included for production deployment. Key differences from the dev/demo compose:

- `DEMO_MODE=false` — disables synthetic scores
- `ALERT_COOLDOWN_SECONDS=60` — enables per-stream suppression
- `MODEL_MODE=ensemble` — uses both models
- `DISABLE_AUTH=false` — enforces API key

Run with:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up
```

---

## Appendix — Key File Map

```
src/
  api/
    app.py                      # FastAPI factory + lifespan
    routes.py                   # V1: /ingest, /alerts, /health, /metrics
    routes_v2.py                # V2: /v2/ingest, /v2/alerts
    schemas.py                  # Pydantic models
    pipeline.py                 # PipelineContainer
    settings.py                 # AppSettings (env-driven)
  runtime/
    inference_engine.py         # V1 InferenceEngine
    pipeline_v2.py              # V2 V2Pipeline + _V2LogTokenizer
    sequence_buffer.py          # Rolling window SequenceBuffer (V1)
    types.py                    # RiskResult
  modeling/
    baseline/
      model.py                  # IsolationForest wrapper
      extractor.py              # BaselineFeatureExtractor
    transformer/
      model.py                  # NextTokenTransformerModel
      scorer.py                 # AnomalyScorer (NLL)
    behavior/
      lstm_model.py             # SystemBehaviorModel (LSTM)
    anomaly/
      autoencoder.py            # AnomalyDetector (Denoising AE)
    severity/
      severity_classifier.py    # SeverityClassifier (MLP)
    embeddings/
      word2vec_trainer.py       # Word2VecTrainer wrapper
  alerts/
    models.py                   # Alert, AlertPolicy dataclasses
    manager.py                  # AlertManager (cooldown + bucketing)
  observability/
    metrics.py                  # MetricsRegistry + MetricsMiddleware
  data_layer/
    models.py                   # LogEvent dataclass
training/
  train_embeddings.py           # Stage 1: Word2Vec
  train_behavior_model.py       # Stage 2: LSTM
  train_autoencoder.py          # Stage 3: Denoising AE
  train_severity_model.py       # Stage 4: Severity MLP
scripts/
  evaluate_v2.py                # V1 vs V2 offline evaluation
docker/
  Dockerfile                    # Python 3.11-slim, port 8000
  docker-compose.yml            # api + prometheus + grafana
  docker-compose.prod.yml       # Production overrides
```
