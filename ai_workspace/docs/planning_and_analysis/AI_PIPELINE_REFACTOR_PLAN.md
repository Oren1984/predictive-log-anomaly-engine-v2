# AI Pipeline Refactor Plan
## Predictive Log Anomaly Engine — OOP AI Pipeline

**Document Type:** Implementation and Gap Analysis Reference
**Assembled from:**
- `IMPLEMENTATION_ACTION_PLAN.md` — Full document (Sections 1-8)
- `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md` — Sections 4, 5, 6, 7, 9, 10, 11

The original source documents remain unchanged. This file consolidates the full implementation roadmap and detailed gap analysis into one reference.

---

## Part A: Implementation Action Plan
*Source: IMPLEMENTATION_ACTION_PLAN.md*

---

# Implementation Action Plan
## Predictive Log Anomaly Engine — OOP AI Pipeline Refactor

**Based on:** `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md`
**Requirements source:** `PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md`
**Date:** 2026-03-06

---

## 1. High-Level Summary

The project is production-grade on its infrastructure side. The FastAPI server, Prometheus/Grafana monitoring, Docker Compose stack, CI/CD pipeline, alert management system, and 233 automated tests are all solid and should not be touched during this refactor.

The problem is the AI learning pipeline. The requirements document specifies six named classes implementing a specific deep learning architecture: Word2Vec embeddings -> LSTM context encoder -> Denoising Autoencoder -> MLP severity classifier. None of these four learning components exist. Instead, the project uses regex-based template IDs (integers, not semantic vectors), an IsolationForest model (not an Autoencoder), a causal Transformer (not an LSTM), and a hard-coded score/threshold ratio rule (not an MLP classifier).

This means the infrastructure layer stays, the API layer stays, and the alert layer stays — but the entire ML learning stack must be rebuilt with a new architecture. The rebuild does not break anything that is already working because the existing models can run in parallel during transition.

---

## 2. What Can Stay As-Is

These components are complete, tested, and already satisfy requirements. Do not modify them.

| Component | Location | Why It Stays |
|---|---|---|
| FastAPI application factory | `src/api/app.py` | Fully functional; all routes work; 233 tests pass |
| API routes and schemas | `src/api/routes.py`, `src/api/schemas.py` | REST contract is stable; only `/ingest` input format may need a minor update |
| Settings / configuration | `src/api/settings.py` | Env-driven config is clean and complete |
| AuthMiddleware | `src/security/auth.py` | API key auth works correctly |
| AlertManager | `src/alerts/manager.py` | Deduplication + cooldown logic is correct and tested |
| Alert + AlertPolicy models | `src/alerts/models.py` | Severity bucket model is reusable even after MLP replaces the rule |
| N8nWebhookClient | `src/alerts/n8n_client.py` | Outbox pattern is correct; just needs activation |
| MetricsRegistry + MetricsMiddleware | `src/observability/metrics.py` | Prometheus counters and histograms are correct and match Grafana dashboard |
| HealthChecker | `src/health/checks.py` | Works correctly |
| Prometheus config | `prometheus/prometheus.yml` | No changes needed |
| Grafana dashboard | `grafana/dashboards/` | No changes needed; only add panels for new metrics later |
| Dockerfile | `Dockerfile` | Works; only update if new dependencies need system packages |
| Docker Compose | `docker-compose.yml` | No changes needed |
| CI/CD workflow | `.github/workflows/ci.yml` | No changes needed |
| Demo UI (HTML) | `templates/index.html`, `src/api/ui.py` | Adequate for now; upgrade in Phase 8 |
| EventTokenizer | `src/parsing/tokenizer.py` | Still needed for `explain()` method in InferenceEngine |
| RegexLogParser / JsonLogParser | `src/parsing/parsers.py` | Still useful as first-pass log structuring before NLP |
| SequenceBuffer | `src/runtime/sequence_buffer.py` | Streaming buffer logic is correct; rewire to new model in Phase 7 |
| RiskResult | `src/runtime/types.py` | Clean data class; keep as-is |
| All existing tests | `tests/` | Must continue passing throughout the entire refactor |

---

## 3. What Needs Refactoring

These components exist and work but need changes to align with the new architecture. None require a full rewrite.

---

**Component: `Pipeline` container**
- Current: `src/api/pipeline.py` — wires `InferenceEngine` + `AlertManager` + `N8nClient` + metrics
- Required change: After the new AI classes are built (Phases 2-6), `Pipeline.load_models()` must load the new `LogPreprocessor`, `SystemBehaviorModel`, `AnomalyDetector`, and `SeverityClassifier` instead of (or alongside) the old `baseline.pkl` and `transformer.pt`
- Difficulty: **Medium** — the Pipeline class structure is fine; only the wiring inside `load_models()` and `process_event()` changes

---

**Component: `InferenceEngine`**
- Current: `src/runtime/inference_engine.py` — loads IsolationForest + Transformer, scores integer token sequences
- Required change: Add a new scoring path that accepts float embedding vectors from `LogPreprocessor`, passes them through `SystemBehaviorModel` -> `AnomalyDetector`, and returns reconstruction error as the anomaly score. The existing `score_baseline()` and `score_transformer()` methods can remain as fallback modes.
- Difficulty: **Medium** — the class structure accommodates multiple scoring modes already

---

**Component: `AlertPolicy.classify_severity()`**
- Current: `src/alerts/models.py` — hard-coded ratio rule: score/threshold >= 1.5x = critical, >= 1.2x = high, >= 1.0x = medium
- Required change: After `SeverityClassifier` MLP is trained (Phase 6), replace this rule with a call to `SeverityClassifier.predict(latent_vector, reconstruction_error)`. The `Alert` dataclass and `AlertManager` do not change — only the severity assignment logic.
- Difficulty: **Low** — one method replacement in one file

---

**Component: `main.py` entrypoint**
- Current: Does not exist as a project-level file. Entry points are `scripts/stage_07_run_api.py` and `scripts/90_run_api.py`
- Required change: Create `main.py` at the project root. It should instantiate the six required classes and start the FastAPI server. Think of it as the "conductor" that wires everything together.
- Difficulty: **Low**

---

**Component: `SlidingWindowSequenceBuilder`**
- Current: `src/sequencing/builders.py` — produces `Sequence` objects with integer token lists
- Required change: After Phase 2 (LogDataset), this class is superseded for training purposes. Keep it for the streaming runtime buffer path. No deletion needed — just stop using it for model training.
- Difficulty: **Low** — no code change, just routing change

---

**Component: Repository structure (duplicate packages)**
- Current: `src/data/` and `src/synthetic/` both contain synthetic data generators. `src/app/` and `src/core/contracts/` are empty.
- Required change: Delete empty packages. Merge `src/data/` into `src/synthetic/`. Create new packages: `src/preprocessing/`, `src/dataset/`, `src/engine/`.
- Difficulty: **Low** — file moves and `__init__.py` cleanup only

---

## 4. What Must Be Built From Scratch

These six components do not exist anywhere in the codebase and must be created as new files.

---

### `LogPreprocessor`

**Purpose**: Convert raw log text into fixed-size float vectors using Word2Vec or FastText semantic embeddings. This replaces the integer token_id representation for ML training purposes.

**Dependencies**: `gensim` (Word2Vec/FastText), existing log corpus at `data/processed/events_unified.csv`

**Inputs**: Raw log message string (the `message` field of `LogEvent`)
**Outputs**: `numpy.ndarray` of shape `[vector_dim]` (e.g., 100-dimensional float vector per log line)

**Where to put it**: `src/preprocessing/log_preprocessor.py`

**Existing code that helps**:
- `src/parsing/template_miner.py` — already has the regex normalization logic (replace IPs, timestamps, hex). Copy these patterns into `LogPreprocessor.clean()`.
- `src/parsing/parsers.py:RegexLogParser` — already extracts the `message` field from raw log lines. Feed its output into `LogPreprocessor`.

**Key methods needed**:
- `clean(raw_text: str) -> str` — normalize text
- `tokenize(text: str) -> list[str]` — word-level split
- `train_embeddings(corpus: list[list[str]])` — train Word2Vec on log corpus
- `embed(tokens: list[str]) -> np.ndarray` — mean-pool word vectors
- `save(path)` / `load(path)` — persist the trained Word2Vec model

---

### `LogDataset`

**Purpose**: Wrap a collection of embedded log sequences into a PyTorch-compatible dataset that returns sliding window tensors suitable for DataLoader batching.

**Dependencies**: `torch.utils.data.Dataset`, output from `LogPreprocessor` (float vectors), `data/intermediate/` embedding files

**Inputs**: List of log embedding arrays + labels; window size and stride parameters
**Outputs**: Per `__getitem__` call: `(torch.FloatTensor[seq_len, vec_dim], label)`. DataLoader produces batches of shape `[batch_size, seq_len, vec_dim]`.

**Where to put it**: `src/dataset/log_dataset.py`

**Existing code that helps**:
- `src/sequencing/builders.py:SlidingWindowSequenceBuilder` — already implements the sliding window logic over a list. The `__init__`, `window`, and `stride` parameters can be directly adapted.
- `src/modeling/transformer/trainer.py:_make_batches()` — shows the existing batching approach. The new `DataLoader` replaces this generator.

**Key methods needed**:
- `__len__()` — number of windows in the dataset
- `__getitem__(idx)` — return `(tensor_window, label)` for the i-th window

---

### `SystemBehaviorModel`

**Purpose**: Learn the temporal behavioral patterns in log sequences using LSTM layers. Produces a "Context Vector" (the LSTM's final hidden state) summarizing the behavioral signature of a window.

**Dependencies**: `torch.nn.LSTM`, output from `LogDataset` (3D float tensors)

**Inputs**: `torch.FloatTensor` of shape `[batch_size, seq_len, vec_dim]`
**Outputs**: Context Vector `torch.FloatTensor` of shape `[batch_size, hidden_dim]` (final LSTM hidden state)

**Where to put it**: `src/modeling/behavior_model.py`

**Existing code that helps**:
- `src/modeling/transformer/model.py:NextTokenTransformerModel` — shows the `nn.Module` save/load pattern (`save()`, `load()`, `forward()`). Copy this pattern exactly.
- `src/modeling/transformer/trainer.py:Trainer` — the training loop structure (AdamW optimizer, loss, early stopping) can be adapted for the LSTM training loop.
- `src/modeling/transformer/config.py:TransformerConfig` — shows how to use a config dataclass. Create a parallel `LSTMConfig` dataclass.

**Key methods needed**:
- `forward(x: FloatTensor) -> FloatTensor` — returns context vector
- `save(path)` / `load(path)` — model persistence

---

### `AnomalyDetector`

**Purpose**: Self-supervised Denoising Autoencoder trained exclusively on normal log sequences. Learns to reconstruct "healthy" behavior. Anomalies produce high reconstruction error.

**Dependencies**: `torch.nn`, output from `SystemBehaviorModel` (context vectors)

**Inputs**: Context Vector `torch.FloatTensor[batch_size, hidden_dim]`
**Outputs**:
- During training: reconstructed vector + MSE loss
- During inference: `(reconstruction_error: float, latent_vector: FloatTensor[latent_dim])`

**Where to put it**: `src/modeling/anomaly_detector.py`

**Existing code that helps**:
- `src/modeling/baseline/model.py:BaselineAnomalyModel` — shows the `fit()` / `score()` / `predict()` interface pattern. Mirror this interface in `AnomalyDetector` so `InferenceEngine` can call it the same way.
- `src/modeling/baseline/calibrator.py` — shows the threshold calibration approach. Adapt for reconstruction error percentile thresholding.
- `src/runtime/types.py:RiskResult` — the `risk_score` field will receive reconstruction error as its value. No changes to `RiskResult` needed.

**Key methods needed**:
- `forward(context_vector) -> (reconstructed, latent)` — Encoder-Decoder forward pass
- `reconstruction_error(original, reconstructed) -> float` — MSE computation
- `fit_threshold(normal_errors: list[float], percentile: float)` — calibrate anomaly threshold from validation set
- `is_anomaly(error: float) -> bool`
- `save(path)` / `load(path)`

---

### `SeverityClassifier`

**Purpose**: Trained MLP that takes the latent vector and reconstruction error from `AnomalyDetector` and classifies anomaly severity into Info, Warning, or Critical using Softmax probabilities.

**Dependencies**: `torch.nn.Linear`, `torch.nn.Dropout`, `torch.nn.Softmax`; output from `AnomalyDetector` (latent vector + reconstruction error); severity-labeled training data

**Inputs**: `[latent_vector (dim=latent_dim) + reconstruction_error (dim=1)]` concatenated = `FloatTensor[latent_dim + 1]`
**Outputs**: `FloatTensor[3]` — probabilities for `[Info, Warning, Critical]`

**Where to put it**: `src/modeling/severity_classifier.py`

**Existing code that helps**:
- `src/alerts/models.py:AlertPolicy.classify_severity()` — the existing thresholds (1.0x, 1.2x, 1.5x ratio) can be used as a labeling heuristic to generate training data for the MLP. Apply this rule to the reconstruction error distribution to auto-label training examples before the MLP is trained.
- `src/modeling/transformer/trainer.py:Trainer` — the training loop pattern is reusable.

**Key methods needed**:
- `forward(features: FloatTensor) -> FloatTensor` — returns 3-class probabilities
- `predict(latent, error) -> str` — returns "info" | "warning" | "critical"
- `save(path)` / `load(path)`

**Blocking dependency note**: This class requires severity-labeled training data. The fastest path is to use the existing `AlertPolicy.classify_severity()` ratio rule to auto-label anomaly windows from the AnomalyDetector output on the training set. This bootstraps the MLP with rule-derived labels initially. Human review or additional labeling can improve it later.

---

### `ProactiveMonitorEngine`

**Purpose**: Top-level orchestrator class that connects all six pipeline stages and exposes the full system to production. Replaces the current `Pipeline` container as the authoritative runtime coordinator.

**Dependencies**: All five classes above + `InferenceEngine` + `AlertManager` + `MetricsRegistry`

**Inputs**: Log stream events (from HTTP POST, file tail, or Kafka in the future)
**Outputs**: Risk scores, severity-classified alerts, Prometheus metrics

**Where to put it**: `src/engine/proactive_engine.py`

**Existing code that helps**:
- `src/api/pipeline.py:Pipeline` — the current `Pipeline.process_event()` and `load_models()` methods are the direct predecessors. `ProactiveMonitorEngine` should absorb `Pipeline`'s responsibilities and add the new model chain.
- `src/observability/metrics.py:MetricsRegistry` — inject into `ProactiveMonitorEngine.__init__()` and record new metrics (reconstruction_error histogram, severity distribution counter).

**Key methods needed**:
- `load_models()` — load all artifacts for all six stages
- `process_event(event: dict) -> dict` — run the full pipeline
- `recent_alerts() -> list[dict]` — delegate to alert buffer
- `metrics_snapshot() -> dict` — return current metric values

---

## 5. Recommended Target Architecture

### Final Folder Structure

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

### Module Interaction Flow

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

## 6. Step-by-Step Implementation Roadmap

---

### Phase 1 — Architecture Alignment

**Goal**: Establish the correct package structure and stub classes. No AI code yet. This phase is about naming, structure, and entrypoint.

**Tasks**:
1. Create `src/preprocessing/__init__.py` + `log_preprocessor.py` (stub class, no logic)
2. Create `src/dataset/__init__.py` + `log_dataset.py` (stub class)
3. Create `src/modeling/behavior_model.py` (stub class)
4. Create `src/modeling/anomaly_detector.py` (stub class)
5. Create `src/modeling/severity_classifier.py` (stub class)
6. Create `src/engine/__init__.py` + `proactive_engine.py` (stub class)
7. Create `main.py` at project root — imports all six classes, starts uvicorn
8. Delete `src/app/` and `src/core/contracts/` (empty packages)
9. Merge `src/data/` into `src/synthetic/` (resolve duplication)
10. Run `pytest -m "not slow"` — all 211 tests must still pass

**Expected result**: Six required class names exist and are importable. `main.py` starts the server. No tests broken.

**Dependencies**: None — this is the first phase.

---

### Phase 2 — NLP Pipeline (LogPreprocessor)

**Goal**: Implement full `LogPreprocessor` — text cleaning, word tokenization, Word2Vec training, mean pooling.

**Tasks**:
1. Add `gensim>=4.3.0` to `requirements.txt`
2. Implement `LogPreprocessor.clean()` — port regex patterns from `src/parsing/template_miner.py`
3. Implement `LogPreprocessor.tokenize()` — word-level split on cleaned text
4. Implement `LogPreprocessor.train_embeddings()` — train Word2Vec on `events_unified.csv` message column (1M-row sample is sufficient; use `data/processed/events_sample_1m.csv`)
5. Implement `LogPreprocessor.embed()` — mean-pool word vectors for a single log line
6. Implement `LogPreprocessor.save()` and `LogPreprocessor.load()` — save Word2Vec model to `models/word2vec.model`
7. Write a training script `scripts/train_embeddings.py` that runs the full embedding pipeline
8. Write unit tests: `tests/unit/test_log_preprocessor.py`

**Expected result**: `LogPreprocessor` produces a 100-dim float vector for any log line. `models/word2vec.model` artifact on disk.

**Dependencies**: Phase 1 complete.

---

### Phase 3 — Sequence Dataset (LogDataset)

**Goal**: Implement `LogDataset` as a proper `torch.utils.data.Dataset` over embedded log windows. Produce working `DataLoader`.

**Tasks**:
1. Implement `LogDataset.__init__()` — accepts list of embedded log arrays + labels + window config
2. Implement `LogDataset.__len__()` and `LogDataset.__getitem__(idx)` — return `(FloatTensor[seq_len, vec_dim], label)`
3. Add `LogDataset.from_csv()` class method — loads `events_sample_1m.csv`, runs `LogPreprocessor.embed()` on each row, builds windows
4. Add `DataLoader` wrapper in a factory function `make_dataloaders(dataset, batch_size, val_split)`
5. Write unit tests: `tests/unit/test_log_dataset.py`
6. Save intermediate embedding arrays to `data/intermediate/log_embeddings.npy` (avoids re-embedding on each run)

**Expected result**: `DataLoader` yields 3D float tensors `[32, 20, 100]` ready for LSTM input.

**Dependencies**: Phase 2 complete (Word2Vec model must exist).

---

### Phase 4 — LSTM Behavior Model (SystemBehaviorModel)

**Goal**: Implement `SystemBehaviorModel` as an LSTM encoder that produces a context vector summarizing a log window.

**Tasks**:
1. Create `LSTMConfig` dataclass: `input_dim`, `hidden_dim`, `num_layers`, `dropout`, `learning_rate`, `max_epochs`, `patience`
2. Implement `SystemBehaviorModel.forward()` — `nn.LSTM` processing 3D input, return final hidden state as context vector
3. Implement `SystemBehaviorModel.save()` and `SystemBehaviorModel.load()` — mirror pattern from `NextTokenTransformerModel`
4. Implement training loop in `scripts/train_behavior_model.py` — train on normal sequences only (label=0); use AdamW + CosineAnnealingLR (copy from `Trainer` in `src/modeling/transformer/trainer.py`)
5. Save trained model to `models/behavior_model.pt`
6. Write unit tests: `tests/unit/test_behavior_model.py`

**Expected result**: `SystemBehaviorModel` produces context vectors `[batch_size, hidden_dim]` from DataLoader batches.

**Dependencies**: Phase 3 complete (DataLoader must be working).

---

### Phase 5 — Autoencoder Anomaly Engine (AnomalyDetector)

**Goal**: Implement `AnomalyDetector` as a Denoising Autoencoder trained on normal behavior. Produces reconstruction error as the anomaly signal.

**Tasks**:
1. Implement `AnomalyDetector` with separate Encoder and Decoder `nn.Sequential` blocks
2. Implement `AnomalyDetector.forward()` — Encoder compresses context vector to latent space; Decoder reconstructs; return `(reconstructed, latent)`
3. Implement `AnomalyDetector.reconstruction_error()` — MSE between original and reconstructed
4. Implement training loop in `scripts/train_anomaly_detector.py` — train on normal context vectors from `SystemBehaviorModel`; use MSE loss
5. Implement `AnomalyDetector.fit_threshold()` — compute anomaly threshold from validation set at 95th percentile of normal reconstruction errors
6. Save model to `models/anomaly_detector.pt` and threshold to `artifacts/threshold_autoencoder.json`
7. Wire into `InferenceEngine`: add a `score_autoencoder(context_vector)` method that calls `AnomalyDetector`
8. Write unit tests: `tests/unit/test_anomaly_detector.py`

**Expected result**: `AnomalyDetector` flags anomalous sequences via reconstruction error. `InferenceEngine` has a new `autoencoder` mode alongside `baseline` and `transformer`.

**Dependencies**: Phase 4 complete (context vectors must be available).

---

### Phase 6 — Severity Classifier (SeverityClassifier)

**Goal**: Implement `SeverityClassifier` as a trained MLP replacing the hard-coded severity ratio rule.

**Tasks**:
1. Generate severity training labels: run `AnomalyDetector` on all anomaly windows, use `AlertPolicy.classify_severity()` ratio rule applied to reconstruction error to auto-label each window as info/warning/critical
2. Implement `SeverityClassifier` MLP: `Linear -> ReLU -> Dropout -> Linear -> ReLU -> Dropout -> Linear -> Softmax`; input dim = `latent_dim + 1`; output dim = 3
3. Implement `SeverityClassifier.predict(latent, error)` — returns `"info"` | `"warning"` | `"critical"`
4. Implement training loop in `scripts/train_severity_classifier.py`; use CrossEntropyLoss + AdamW
5. Save model to `models/severity_classifier.pt`
6. Replace `AlertPolicy.classify_severity()` call in `src/alerts/models.py:AlertPolicy.risk_to_alert()` with `SeverityClassifier.predict()` call
7. Write unit tests: `tests/unit/test_severity_classifier.py`

**Expected result**: Severity is assigned by a trained MLP, not a ratio rule. Alert severity output is probabilistic.

**Dependencies**: Phase 5 complete (latent vectors and reconstruction errors must be available).

---

### Phase 7 — Engine Integration (ProactiveMonitorEngine)

**Goal**: Wire all six classes into `ProactiveMonitorEngine` and connect to the FastAPI pipeline. Replace the current `Pipeline` container.

**Tasks**:
1. Implement `ProactiveMonitorEngine.load_models()` — load `LogPreprocessor`, `SystemBehaviorModel`, `AnomalyDetector`, `SeverityClassifier` (and optionally existing `BaselineAnomalyModel` and `NextTokenTransformerModel` as fallbacks)
2. Implement `ProactiveMonitorEngine.process_event(event)` — full pipeline: clean text -> embed -> buffer -> context vector -> reconstruction error -> severity -> alert
3. Update `src/api/pipeline.py` to instantiate `ProactiveMonitorEngine` instead of `InferenceEngine` directly (or make `Pipeline` a thin wrapper over `ProactiveMonitorEngine`)
4. Add new Prometheus metrics: `reconstruction_error_histogram`, `severity_info_total`, `severity_warning_total`, `severity_critical_total`
5. Update Settings: add `MODEL_MODE=autoencoder` as a valid mode
6. Run full test suite — all 233 tests must pass
7. Run Docker Compose smoke test end-to-end
8. Update `scripts/stage_07_run_api.py` and `main.py` to use the new engine

**Expected result**: Full six-stage pipeline is live behind the FastAPI server. Existing tests pass. Docker stack starts cleanly.

**Dependencies**: Phases 1-6 complete.

---

### Phase 8 — UI Preparation

**Goal**: Make the API surface ready for a richer UI layer and optionally add a Streamlit prototype.

**Tasks**:
1. Add `GET /ws/alerts` WebSocket endpoint to FastAPI — push alert events in real-time to connected clients
2. Add `GET /pipeline/status` endpoint — returns current model load status, mode, threshold values
3. Add `GET /score/history` endpoint — returns last N risk scores and reconstruction errors as a timeseries
4. Create `src/ui/` package with `README.md` describing the intended Streamlit approach
5. Add `streamlit` to `requirements-dev.txt` (not production)
6. Optionally: create `src/ui/dashboard.py` as a Streamlit app that calls the FastAPI endpoints and displays live alerts, score charts, and log upload widget
7. Update `templates/index.html` to use the new `/ws/alerts` WebSocket for live alert push

**Expected result**: API is fully UI-ready. Optional Streamlit dashboard provides live monitoring view without any backend changes.

**Dependencies**: Phase 7 complete.

---

## 7. Risk Assessment

**Risk 1 — Integer-to-float data representation change (HIGH)**

The current pipeline uses a single integer (`token_id`) per log event. Every component from `SequenceBuffer` to `InferenceEngine.ingest()` is built around this. Switching to float vectors requires `SequenceBuffer` to store float arrays instead of integers. This touches the hot path of the streaming system. Mitigation: implement the new embedding path as a parallel code path inside `InferenceEngine` (a new `autoencoder` mode) rather than modifying the existing `baseline`/`transformer` modes. Keep old modes working throughout the transition.

**Risk 2 — Existing slow tests depend on model artifacts (MEDIUM)**

22 tests are marked `@pytest.mark.slow` and require `models/baseline.pkl` and `models/transformer.pt`. After the new pipeline is active, these tests will still reference the old artifacts. Mitigation: do not delete old model files until the new models are trained and validated. Update slow tests in Phase 7 once new artifacts exist.

**Risk 3 — SeverityClassifier requires label bootstrap (MEDIUM)**

The dataset has no severity labels — only binary (0=normal, 1=anomaly). The MLP classifier cannot be trained without severity-labeled data. Mitigation: use the auto-labeling approach described in Phase 6 Task 1 — apply the existing `AlertPolicy` ratio rule to reconstruction errors to generate synthetic severity labels. This is a known approximation. Document it clearly. Human review of labels is a future improvement, not a blocker.

**Risk 4 — Word2Vec training on 15.9M rows (MEDIUM)**

Training Word2Vec on the full `events_unified.csv` (15.9M rows) requires significant time and memory (~4-6 GB based on current dataset memory profiles). Mitigation: use the existing 1M-row sample (`data/processed/events_sample_1m.csv`) for initial embedding training. This is already used in the `ai_workspace/` stage scripts and is known to be manageable.

**Risk 5 — Docker image size increase (LOW)**

Adding `gensim` and trained Word2Vec model files will increase Docker image and artifact size. Mitigation: add `gensim` to requirements and mount `models/word2vec.model` as a volume (same pattern as existing `models/` volume in `docker-compose.yml`). No Dockerfile changes needed.

**Risk 6 — CI test suite slow due to new model loading (LOW)**

Phase 3-6 will add new model-dependent tests. Mitigation: mark all new model-dependent tests with `@pytest.mark.slow` from the start. The fast CI suite (`pytest -m "not slow"`) will continue to run in under 15 seconds.

---

## 8. Final Recommendation

**Partial replacement of the ML pipeline. Keep all infrastructure.**

The existing `IsolationForest` model and `NextTokenTransformerModel` should be kept as operational fallbacks, not deleted. They provide a working baseline for comparison and allow the system to continue running during the transition.

The new architecture (LSTM -> Autoencoder -> MLP) must be built as a new parallel code path inside `InferenceEngine` (a new `autoencoder` mode). Once the new pipeline is validated — meaning it produces better or comparable anomaly detection metrics vs. the IsolationForest on the BGL and HDFS datasets — the old models can be deprecated and eventually removed.

The reason for keeping old models initially:
1. The new pipeline depends on Word2Vec training quality. If the embeddings are poor, the downstream LSTM and Autoencoder will perform worse than IsolationForest. Keeping IsolationForest as a fallback ensures the system never degrades below the current baseline.
2. Existing tests (particularly the 22 slow tests) rely on the old model files. Keeping the models prevents test breakage during transition.
3. The `InferenceEngine` already supports multiple modes (`baseline`, `transformer`, `ensemble`). Adding `autoencoder` mode is a natural extension, not a breaking change.

Once Phase 7 is complete and the new pipeline is confirmed to work, add an `EVALUATION.md` document that compares the two approaches on the BGL/HDFS validation sets. Use that comparison to decide whether to retire the old models or keep the ensemble as permanent.

The overall decision: **targeted replacement of learning components with architectural continuity of the infrastructure layer**.

---

## Part B: Repository Gap Analysis — Detailed Analysis
*Source: REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md — Sections 4, 5, 6, 7, 9, 10, 11*

---

## 4. Gap Analysis

### Full Comparison Table

| Requirement | Exists Today | Partially Exists | Missing | Notes / Evidence | Recommended Action |
|---|---|---|---|---|---|
| **Python-only implementation** | Yes | - | - | `requirements.txt`, all `.py` files | No action needed |
| **OOP architecture (general)** | Partial | Yes | - | 15+ classes in `src/`, but procedural scripts in `ai_workspace/` and `scripts/` | Consolidate scripts into classes |
| **`LogPreprocessor` class** | No | - | Yes | Nothing resembling this name exists anywhere in `src/` | Create from scratch |
| **Text cleaning (lowercase, normalize)** | Partial | Yes | - | `src/parsing/parsers.py:RegexLogParser` does pattern matching but no NLP normalization | Extend or replace |
| **Tokenizer** | Partial | Yes | - | `src/parsing/tokenizer.py:EventTokenizer` does template_id->token_id mapping, not word-level tokenization | Different paradigm; needs Word2Vec tokenizer added |
| **Word2Vec / FastText embeddings** | No | - | Yes | Not referenced anywhere in the project | New component: train or load embeddings |
| **Mean Pooling aggregation** | No | - | Yes | Sequences use raw integer token IDs, not pooled float vectors | New component |
| **`LogDataset` (torch.utils.data.Dataset)** | No | - | Yes | `src/sequencing/builders.py:SlidingWindowSequenceBuilder` exists but is not a PyTorch Dataset | New class needed |
| **PyTorch DataLoader batching** | No | - | Yes | `src/modeling/transformer/trainer.py` has `_make_batches()` (a plain generator, not DataLoader) | Replace with DataLoader |
| **3D Tensor [B, T, V] input** | No | - | Yes | Current Transformer input is 2D: [B, T] token IDs, not float vectors | Architecture change required |
| **`SystemBehaviorModel` (LSTM/RNN)** | No | - | Yes | `src/modeling/transformer/model.py:NextTokenTransformerModel` is a Transformer, not LSTM | New model class needed |
| **LSTM Hidden State / Context Vector** | No | - | Yes | Transformer produces logits, not a context vector for downstream use | New architecture |
| **`AnomalyDetector` (Denoising Autoencoder)** | No | - | Yes | `src/modeling/baseline/model.py:BaselineAnomalyModel` uses IsolationForest | Replacement required |
| **Reconstruction Error thresholding** | No | - | Yes | Current system uses IsolationForest anomaly scores | Different mechanism |
| **Encoder / Decoder / Latent Space** | No | - | Yes | No Autoencoder architecture exists anywhere | New component |
| **`SeverityClassifier` (MLP + Softmax)** | No | - | Yes | `src/alerts/models.py:AlertPolicy.classify_severity()` is a hard-coded ratio rule | Replacement required |
| **Three-class output (Info/Warning/Critical)** | Partial | Yes | - | `AlertPolicy` uses critical/high/medium/low buckets | Rename + replace logic |
| **Latent Space + Reconstruction Error as MLP input** | No | - | Yes | No latent space exists | Requires Stage 4 first |
| **Dropout in classifier** | No | - | Yes | No dropout in any classifier layer | New component |
| **`ProactiveMonitorEngine` class** | Partial | Yes | - | Functionality split across `Pipeline`, `InferenceEngine`, `MetricsRegistry` | Consolidation and rename |
| **Live log stream (Kafka / Logstash / file tail)** | No | - | Yes | Current ingest is HTTP POST only (REST API) | New ingestion adapter |
| **Prometheus metrics export** | Yes | - | - | `src/observability/metrics.py:MetricsRegistry` + `/metrics` endpoint | No action needed |
| **Grafana dashboard** | Yes | - | - | `grafana/dashboards/stage08_api_observability.json` | Extend with new metrics |
| **Alert notifications (Slack/Email)** | Partial | Yes | - | `src/alerts/n8n_client.py:N8nWebhookClient` (dry-run outbox) | Activate or replace with real notifier |
| **`main.py` single entrypoint** | No | - | Yes | `scripts/stage_07_run_api.py` exists but is scattered; no clear project-level `main.py` | Create clean entrypoint |
| **Modular class-per-stage design** | Partial | Yes | - | API layer is modular; ML pipeline is fragmented across `ai_workspace/` scripts | Refactor |
| **Docker containerization** | Yes | - | - | `Dockerfile`, `docker-compose.yml` | No action needed |
| **CI/CD pipeline** | Yes | - | - | `.github/workflows/ci.yml` | No action needed |
| **Test coverage** | Yes | - | - | 233 tests (unit + integration) | Extend tests for new components |
| **UI entrypoint** | Partial | Yes | - | `templates/index.html` (demo page) + `/` route | Needs richer interaction |

---

## 5. OOP and Architecture Review

### Is the Project Truly Object-Oriented?

**Partially yes.** The project has strong OOP in its API and infrastructure layer, and weaker OOP in its ML/data pipeline.

#### Strongly OOP (good class design):

| Class | Location | Assessment |
|---|---|---|
| `InferenceEngine` | `src/runtime/inference_engine.py` | Well-designed: encapsulates buffer + scoring + thresholding; uses dependency injection via constructor |
| `SequenceBuffer` | `src/runtime/sequence_buffer.py` | Clean single-responsibility: LRU deque buffer per stream key |
| `AlertManager` | `src/alerts/manager.py` | Clean: deduplication + cooldown + statistics |
| `AlertPolicy` | `src/alerts/models.py` | Good: separates policy rules from execution |
| `Pipeline` | `src/api/pipeline.py` | Good facade: wires engine + manager + metrics |
| `MetricsRegistry` | `src/observability/metrics.py` | Good: private registry per instance prevents test conflicts |
| `BaselineAnomalyModel` | `src/modeling/baseline/model.py` | Good: thin wrapper with fit/score/predict/save/load |
| `NextTokenTransformerModel` | `src/modeling/transformer/model.py` | Good: clean `nn.Module` subclass |
| `Trainer` | `src/modeling/transformer/trainer.py` | Good: training loop isolated |
| `LogParser` / `RegexLogParser` | `src/parsing/parsers.py` | Good: ABC + concrete implementation |
| `EventTokenizer` | `src/parsing/tokenizer.py` | Good: encapsulates template_id <-> token_id mapping |

#### Procedural / Script-Based (weak OOP):

| File | Location | Problem |
|---|---|---|
| `run_sampling.py` | `ai_workspace/stage_21_sampling/` | Top-level procedural script; no classes |
| `run_template_mining.py` | `ai_workspace/stage_22_template_mining/` | Top-level procedural script |
| `run_sequence_builder.py` | `ai_workspace/stage_23_sequence_builder/` | Top-level procedural script |
| `run_baseline_model.py` | `ai_workspace/stage_24_baseline_model/` | Top-level procedural script |
| `run_evaluation.py` | `ai_workspace/stage_25_evaluation/` | Top-level procedural script |
| `run_hdfs_supervised_v1.py` | `ai_workspace/stage_26_hdfs_supervised/` | Top-level procedural script |
| `stage_01_data.py` | `scripts/` | Procedural script |
| `stage_04_baseline.py` | `scripts/` | Procedural script |
| `stage_04_transformer.py` | `scripts/` | Procedural script |

All `ai_workspace/` scripts are exploratory notebooks converted to scripts. They have no class boundaries and are not importable as library code.

### Empty or Placeholder Packages

Two packages have no implementations:
- `src/app/__init__.py` — empty
- `src/core/contracts/__init__.py` — empty

These were likely intended for future abstractions but were never populated.

### Recommended Target Class/Module Boundaries

Per the requirements document, the refactored design should follow these class boundaries:

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

---

## 6. AI Pipeline Alignment Review

### Stage 1: NLP Embedding

**Requirement**: `LogPreprocessor` class. Text cleaning (lowercase, normalize IPs/dates to `[IP]`/`[TIMESTAMP]`). Tokenization. Word2Vec/FastText training on log corpus. Mean Pooling to produce a single fixed-size vector per log line.

**What exists now**:
- `src/parsing/parsers.py:RegexLogParser` — parses log lines into `LogEvent` objects (timestamp, level, message). No NLP normalization.
- `src/parsing/template_miner.py` — regex-based template mining (replaces IPs, hex, numbers with placeholders like `<IP>`, `<HEX>`).
- `src/parsing/tokenizer.py:EventTokenizer` — maps integer template_ids to integer token_ids. Not word-level.
- `ai_workspace/stage_22_template_mining/run_template_mining.py` — procedural script that creates `templates.csv` with 7,833 templates using 9-step regex substitution.

**What is missing**:
- Word-level tokenization of log text
- Word2Vec or FastText model (training or loading pre-trained)
- Dense vector representation per log line (currently: single integer token_id)
- Mean Pooling aggregation across word vectors
- The `LogPreprocessor` class itself

**Assessment**: The current approach (regex template mining -> integer IDs) is fundamentally different from the NLP embedding approach. It is effective for pattern matching but does not produce semantic vector embeddings. The two approaches are not compatible at the data representation level — a full replacement of the text-to-number pipeline is required.

**Action Required**: Full replacement (new class, new approach).

---

### Stage 2: Sequence Data Preparation

**Requirement**: `LogDataset` inheriting `torch.utils.data.Dataset`. Sliding window generator. `__len__` and `__getitem__` methods. 3D PyTorch Tensor output `[Batch_Size, Sequence_Length, Vector_Size]`. `DataLoader` wrapping for batching and shuffling.

**What exists now**:
- `src/sequencing/builders.py:SlidingWindowSequenceBuilder` — produces `Sequence` objects (list of token_ids). Does not inherit `torch.utils.data.Dataset`. Not batched.
- `src/runtime/sequence_buffer.py:SequenceBuffer` — streaming sliding window for live inference. Per-stream-key deque. Not a Dataset.
- `src/modeling/transformer/trainer.py:_make_batches()` — a plain Python generator that pads sequences and yields `(input_ids, target_ids, mask)` tuples. Not a `DataLoader`.

**What is missing**:
- `LogDataset(torch.utils.data.Dataset)` class
- `__getitem__` returning a float vector tensor, not an integer token tensor
- 3D tensor output `[B, Seq_Len, Vec_Size]` (current is 2D `[B, Seq_Len]`)
- `torch.utils.data.DataLoader` usage for batching/shuffling

**Assessment**: The sequencing infrastructure exists in spirit (sliding windows, batching), but the current design is incompatible with Stage 1's vector embeddings. Once Word2Vec embeddings are produced, the `LogDataset` class needs to wrap them. The current `SlidingWindowSequenceBuilder` operates on integer sequences; it would need to be replaced by a proper Dataset over float vectors.

**Action Required**: New class inheriting `torch.utils.data.Dataset`. Depends on Stage 1 completion.

---

### Stage 3: Sequence Modeling (LSTM/RNN)

**Requirement**: `SystemBehaviorModel` class. LSTM or RNN layers processing sequences step-by-step. Produces a "Context Vector" summarizing the window. Dense output projection.

**What exists now**:
- `src/modeling/transformer/model.py:NextTokenTransformerModel` — GPT-style causal Transformer (Transformer Encoder + causal mask). Purpose: next-token prediction for anomaly scoring via NLL. Does NOT produce a context vector for downstream use.

**What is missing**:
- `SystemBehaviorModel` class
- LSTM or RNN architecture
- Context vector output (the LSTM's final hidden state or `[CLS]` equivalent)
- The concept of a context vector passed to Stage 4

**Assessment**: The existing Transformer serves a completely different purpose (next-token probability scoring) compared to the LSTM's required role (behavioral context encoder feeding into an Autoencoder). These two architectures are not interchangeable. The Transformer approach is arguably more powerful, but it is not the architecture specified by the requirements document.

**Action Required**: New class `SystemBehaviorModel` with LSTM/RNN layers. The existing Transformer can coexist as an alternative scoring method.

---

### Stage 4: Anomaly Detection (Denoising Autoencoder)

**Requirement**: `AnomalyDetector` class. Encoder compresses context vector into latent space. Decoder reconstructs from latent space. Reconstruction error as the anomaly signal. Threshold on reconstruction error triggers "anomaly flag."

**What exists now**:
- `src/modeling/baseline/model.py:BaselineAnomalyModel` — wrapper around scikit-learn `IsolationForest`. Score = negated `score_samples()`. Anomaly flag = score >= threshold.
- `src/modeling/baseline/extractor.py:BaselineFeatureExtractor` — computes frequency-based features (sequence_length, unique_count, entropy, top-K token counts) as a feature matrix for IsolationForest.

**What is missing**:
- PyTorch-based Autoencoder architecture (Encoder + Decoder)
- Latent space / bottleneck
- Reconstruction error metric (MSE between input and reconstructed output)
- Training on "healthy" sequences only (unsupervised denoising)
- Thresholding on reconstruction error
- Exposure of the latent vector for use by Stage 5

**Assessment**: IsolationForest is an unsupervised anomaly detector based on isolation depth, while a Denoising Autoencoder is a deep learning model that learns to reconstruct normal patterns. They address the same problem with different mechanisms. The IsolationForest approach is simpler, faster, and already functional. The Autoencoder approach is more powerful for high-dimensional vector inputs and integrates with the LSTM context vector from Stage 3. The two approaches are architecturally incompatible — the Autoencoder requires float vector inputs (from Stage 1 embeddings), while IsolationForest currently uses discrete frequency features.

**Action Required**: New class `AnomalyDetector` as a `nn.Module`. The existing IsolationForest can remain as a fallback/comparison baseline.

---

### Stage 5: Severity Classification (MLP)

**Requirement**: `SeverityClassifier` class. MLP (Multi-Layer Perceptron) architecture. Input: concatenation of Latent Vector + Reconstruction Error. Hidden layers with Dropout. Softmax output layer. Three output classes: Info, Warning, Critical.

**What exists now**:
- `src/alerts/models.py:AlertPolicy.classify_severity()` — rule-based: computes `score / threshold` ratio, then maps to severity bucket using hard-coded multipliers (critical >= 1.5x, high >= 1.2x, medium >= 1.0x). This is a function, not a learned model.

**What is missing**:
- `SeverityClassifier` class (PyTorch `nn.Module`)
- Training loop for severity classification
- Ground-truth severity labels for training
- Softmax probability output
- Dropout regularization
- The concept of "Info" as a severity (current system has "medium/high/critical/low")

**Assessment**: The rule-based severity classification is pragmatic and works without labeled severity data. A trained MLP requires labeled examples of Info/Warning/Critical events, which do not currently exist in the dataset (the dataset only has binary labels: 0=normal, 1=anomaly). Creating training data for the MLP would require either manual labeling or a severity labeling heuristic. This is the most blocked stage — it depends on Stages 1-4 and on creating severity-labeled data.

**Action Required**: New class `SeverityClassifier` as `nn.Module`. Also requires severity-labeled training data creation.

---

### Stage 6: AIOps Infrastructure

**Requirement**: `ProactiveMonitorEngine` class. Live log stream ingestion (Kafka, Logstash, or file tail). Metrics export to Prometheus. Grafana visualization. AlertManager notifications (Slack/Email).

**What exists now**:
- `src/observability/metrics.py:MetricsRegistry` — Prometheus counters and histograms. Fully functional.
- `src/api/pipeline.py:Pipeline` — container for InferenceEngine + AlertManager + N8nClient.
- `src/api/app.py:create_app()` — FastAPI factory. Lifespan-based model loading.
- `src/api/routes.py` — `/ingest`, `/alerts`, `/health`, `/metrics` endpoints.
- `src/alerts/n8n_client.py:N8nWebhookClient` — outbox-pattern webhook client (dry-run by default).
- `docker-compose.yml` — api + prometheus + grafana stack.
- `grafana/dashboards/stage08_api_observability.json` — 5-panel dashboard.

**What is missing**:
- A single class named `ProactiveMonitorEngine` (functionality is distributed)
- Live log stream input (Kafka consumer, Logstash adapter, file tail)
- Real-time Slack/Email alert delivery (n8n client is a stub)

**Assessment**: The AIOps infrastructure is the most complete stage relative to the requirements. The Prometheus/Grafana stack is production-ready. The main gap is (1) the class name consolidation into `ProactiveMonitorEngine`, (2) the live log stream input (current design requires HTTP POSTs, not a streaming consumer), and (3) activating real notifications.

**Action Required**: Light refactor — extract `ProactiveMonitorEngine` wrapper. Add streaming input adapter. Activate real notifications.

---

## 7. Repository Structure Review

### Folder Organization Assessment

| Folder | Purpose | Assessment |
|---|---|---|
| `src/` | Main application source | Good. Well-structured packages. |
| `src/api/` | FastAPI app | Good. Separation of routes, schemas, settings, pipeline. |
| `src/modeling/` | ML models | Good. Two separate sub-packages (baseline, transformer). |
| `src/runtime/` | Streaming inference | Good. Clear responsibility. |
| `src/alerts/` | Alert system | Good. Models, manager, and n8n client separated. |
| `src/parsing/` | Log parsing + tokenization | Adequate. Mixed concerns (parsing + tokenization together). |
| `src/sequencing/` | Sequence builders | Adequate. Naming slightly confusing vs `runtime/sequence_buffer`. |
| `src/data/` | Synthetic data generators | Redundant with `src/synthetic/`. Duplicate packages. |
| `src/synthetic/` | Synthetic data generators | Redundant with `src/data/`. |
| `src/app/` | Empty placeholder | Dead code. Remove or populate. |
| `src/core/contracts/` | Empty placeholder | Dead code. Remove or populate. |
| `src/data_layer/` | LogEvent model, loader | Adequate but thin. |
| `ai_workspace/` | Exploratory notebooks-as-scripts | Separate from production code. Good for research isolation. |
| `scripts/` | CLI runners | Mixed: some bridge to `src/`, some standalone. Naming scheme inconsistent. |
| `tests/` | Automated tests | Reasonable. unit/ + integration/ separation is good. |
| `models/` | Runtime model artifacts | Correct location. |
| `artifacts/` | vocab.json, thresholds | Correct location. |
| `data/` | Raw, processed, intermediate data | Correct structure. |
| `templates/` | HTML UI templates | Correct location. |

### Naming Consistency Issues

1. **Two `data` packages**: `src/data/` and `src/synthetic/` appear to be duplicates. `src/data/` has `synth_generator.py` and `src/synthetic/` has `generator.py`. This is redundant.
2. **Scripts naming**: `scripts/` has both numbered (`10_download_data.py`) and named (`stage_01_data.py`) conventions. Inconsistent.
3. **`ai_workspace/` vs `scripts/`**: Unclear boundary. `ai_workspace/` is research; `scripts/` is production CLI. This distinction is not obvious from the directory name.
4. **Empty packages**: `src/app/` and `src/core/contracts/` have no implementations. They add noise.

### Recommended Target Structure

Per the requirements, the structure should be reorganized around the six stages:

```
predictive-log-anomaly-engine/
|-- src/
|   |-- preprocessing/          # Stage 1: LogPreprocessor
|   |-- dataset/                # Stage 2: LogDataset
|   |-- modeling/
|   |   |-- behavior_model.py   # Stage 3: SystemBehaviorModel (LSTM)
|   |   |-- anomaly_detector.py # Stage 4: AnomalyDetector (Autoencoder)
|   |   |-- severity_classifier.py # Stage 5: SeverityClassifier (MLP)
|   |-- engine/                 # Stage 6: ProactiveMonitorEngine
|   |-- api/                    # FastAPI app (keep)
|   |-- alerts/                 # Alert system (keep)
|   |-- observability/          # Metrics (keep)
|   |-- runtime/                # Streaming buffer (keep, rewire)
|   |-- parsing/                # Parser + Tokenizer (keep, extend)
|-- main.py                     # Clean single entrypoint
|-- scripts/                    # Training CLI scripts
|-- tests/                      # Tests (keep)
|-- models/                     # Trained model artifacts
|-- artifacts/                  # JSON artifacts
|-- data/                       # Data files
|-- prometheus/, grafana/, templates/ # Infrastructure (keep)
|-- Dockerfile, docker-compose.yml   # DevOps (keep)
```

---

## 9. Prioritized Action Plan

### Phase 1: Critical Alignment Items

**Objective**: Establish the six required class names and fundamental architectural boundaries before any AI pipeline work.

**Why it matters**: The requirements document defines a contract. Without the correct class names and module boundaries, all subsequent work will be misaligned. Establishing boundaries first allows parallel development.

**Concrete Tasks**:
1. Create `src/preprocessing/log_preprocessor.py` with stub `LogPreprocessor` class (text cleaning + normalization methods)
2. Create `src/dataset/log_dataset.py` with stub `LogDataset(torch.utils.data.Dataset)` class
3. Create `src/modeling/behavior_model.py` with stub `SystemBehaviorModel` class
4. Create `src/modeling/anomaly_detector.py` with stub `AnomalyDetector` class
5. Create `src/modeling/severity_classifier.py` with stub `SeverityClassifier` class
6. Create `src/engine/proactive_engine.py` with stub `ProactiveMonitorEngine` class
7. Create `main.py` at project root — imports and instantiates all six classes

**Expected Outcome**: The six required class names exist. The project structure mirrors the requirements document. Stubs are importable and testable.

---

### Phase 2: Structural Refactor Items

**Objective**: Clean up structural noise in the repository before adding new components.

**Why it matters**: The current dual `src/data/` + `src/synthetic/` packages, empty placeholder packages, and inconsistent `scripts/` naming will cause confusion during refactoring. Clean structure reduces cognitive overhead.

**Concrete Tasks**:
1. Remove or consolidate `src/data/` and `src/synthetic/` (duplicate packages)
2. Remove empty `src/app/` and `src/core/contracts/` packages
3. Standardize `scripts/` naming to `stage_XX_name.py` convention
4. Move all `ai_workspace/` exploratory scripts behind a `research/` label to make the boundary explicit
5. Establish `src/preprocessing/` as the canonical home for all log parsing and NLP

**Expected Outcome**: Clean, non-redundant package structure. New contributors can navigate the codebase without confusion.

---

### Phase 3: AI Pipeline Completion Items

**Objective**: Implement the full six-stage AI pipeline per the requirements document, replacing or supplementing existing ML components.

**Why it matters**: The current IsolationForest + Transformer pipeline does not implement the architecture specified. The new deep learning pipeline (LSTM + Autoencoder + MLP) is the core deliverable of the requirements.

**Concrete Tasks**:

**3A — NLP Embedding (LogPreprocessor)**:
1. Add `gensim` to `requirements.txt` for Word2Vec/FastText
2. Implement text cleaning: lowercase, replace IPs/timestamps/numbers with `[IP]`, `[TIMESTAMP]`, `[NUM]`
3. Train Word2Vec on the BGL/HDFS log corpus (use existing `events_unified.csv`)
4. Implement Mean Pooling: average word vectors for each log line
5. Produce an embedding file: `data/intermediate/log_embeddings.npy`

**3B — Sequence Data Prep (LogDataset)**:
1. Implement `LogDataset.__len__()` and `__getitem__()` returning `torch.FloatTensor` windows
2. Wrap with `torch.utils.data.DataLoader` (batch_size=32, shuffle=True)
3. Produce 3D tensor shape: `[32, 20, 100]` (batch, sequence, vector_dim)

**3C — Sequence Modeling (SystemBehaviorModel)**:
1. Implement `SystemBehaviorModel` with `nn.LSTM` layers
2. Extract the final hidden state as the "Context Vector"
3. Add a dense projection layer to reshape for Autoencoder input
4. Train on normal sequences; validate on held-out normal data

**3D — Anomaly Detection (AnomalyDetector)**:
1. Implement Encoder-Decoder Autoencoder with configurable latent dimension
2. Train exclusively on "normal" (label=0) sequences
3. Compute reconstruction MSE at inference time
4. Fit anomaly threshold from validation set (percentile of normal error distribution)
5. Expose `latent_vector` and `reconstruction_error` for Stage 5

**3E — Severity Classification (SeverityClassifier)**:
1. Design severity labeling strategy (e.g., use reconstruction error magnitude to bin into Info/Warning/Critical)
2. Implement MLP: `[latent_dim + 1]` input -> hidden layers -> Softmax(3)
3. Add Dropout regularization
4. Train on anomaly windows with severity labels
5. Replace `AlertPolicy.classify_severity()` rule with model inference

**Expected Outcome**: Full deep learning pipeline operational. All six required classes implemented. End-to-end inference from raw log text to severity-classified alert.

---

### Phase 4: UI Preparation Items

**Objective**: Prepare the project for a future production UI layer without building it prematurely.

**Why it matters**: A UI built on an unstable AI pipeline will have to be rebuilt. Prepare the hooks first.

**Concrete Tasks**:
1. Add WebSocket endpoint to FastAPI: `GET /ws/alerts` — stream live alerts to clients
2. Add `GET /pipeline/status` endpoint returning current model states and metrics summary
3. Add `GET /score/history` endpoint returning recent risk score timeseries
4. Document all API endpoints in `docs/api_reference.md`
5. Create a placeholder `src/ui/` package with a `README.md` describing the intended UI approach
6. Add `streamlit` to `requirements-dev.txt` (not production) for prototyping

**Expected Outcome**: The API surface is ready for a UI to consume. Adding Streamlit or Gradio becomes a one-day task.

---

### Phase 5: Documentation Alignment

**Objective**: Update all project documentation to reflect the refactored architecture.

**Why it matters**: The current documentation (README, `ai_workspace/reports/`) describes the pre-refactor architecture. After Phase 3, documentation will be outdated.

**Concrete Tasks**:
1. Update `README.md` to describe the six-stage architecture per the requirements document
2. Update `ai_workspace/system_design/architecture.md` with the new class diagram
3. Create `docs/pipeline_architecture.md` with stage-by-stage description
4. Create `docs/training_guide.md` covering how to train Word2Vec, LSTM, Autoencoder, and MLP
5. Update `docs/api_reference.md` with all endpoints
6. Archive (do not delete) the current stage-based reports in `ai_workspace/reports/`

**Expected Outcome**: Documentation accurately describes the current system. New contributors can onboard without confusion.

---

## 10. Risks and Refactor Warnings

### What Must Not Be Broken

| Component | Risk Level | Reason |
|---|---|---|
| FastAPI application factory (`create_app`) | High | 233 tests depend on it |
| `InferenceEngine.ingest()` API contract | High | All integration tests call this |
| `AlertManager` / `AlertPolicy` | Medium | Core alert logic is tested; has real cooldown semantics |
| Prometheus metrics endpoints | Medium | Grafana dashboards depend on metric names |
| `tests/` test suite | High | 233 tests must continue to pass throughout refactor |
| `Dockerfile` + `docker-compose.yml` | Medium | CI/CD smoke test depends on Docker build succeeding |

### Risky Areas

1. **Data representation change (int tokens -> float vectors)**: This is the deepest architectural change. The entire pipeline currently uses `token_id` (integer) as its fundamental unit. Switching to float embeddings requires changing `LogEvent`, `Sequence`, `SequenceBuffer`, `InferenceEngine.ingest()`, and all training scripts. This will break many existing components if not done carefully.

2. **Model artifact incompatibility**: Existing `models/baseline.pkl` and `models/transformer.pt` are trained on integer sequences. After Stage 1 embedding, these models become unusable. Tests marked `@pytest.mark.slow` that depend on model files will all need to be updated.

3. **Feature matrix shape mismatch**: `BaselineFeatureExtractor` produces 204-feature vectors from integer token frequencies. The Autoencoder will expect float embedding vectors of a different shape. The `InferenceEngine._load_baseline_model()` method will fail silently if the feature shapes differ.

4. **Test coverage loss during transition**: If Phase 3 replaces classes, existing tests that pass today may need to be rewritten. Maintain the test suite continuously — do not defer test updates to the end.

5. **`SeverityClassifier` requires labeled data that does not exist**: The BGL/HDFS datasets only have binary labels (0=normal, 1=anomaly). Severity labels (Info/Warning/Critical) are not present. A labeling strategy must be defined before Phase 3E can proceed.

### What Can Remain As-Is For Now

| Component | Justification |
|---|---|
| `AlertManager` + `AlertPolicy` | Functionally complete; rule-based severity can remain until Stage 5 MLP is ready |
| `MetricsRegistry` + Prometheus stack | Already meets requirements; no changes needed |
| `Dockerfile` + `docker-compose.yml` + CI | Production-ready; only update after major structural changes |
| `templates/index.html` demo UI | Adequate for demonstration; replace in Phase 4 |
| `EventTokenizer` | Can coexist; template_id mapping is still useful for the `explain()` method |
| `RegexLogParser` + `JsonLogParser` | Can coexist; feeding into LogPreprocessor |
| `SequenceBuffer` (streaming) | Core runtime component; wire to new embedding pipeline |

### Must Change Now vs Can Postpone

**Must change now (Phase 1 + 2)**:
- Create six stub classes with correct names (blocks all other work)
- Clean up empty packages and duplicates (reduces confusion during refactor)
- Create `main.py` entrypoint

**Can be postponed to Phase 3**:
- Word2Vec/FastText training (requires significant compute and corpus prep)
- LSTM implementation (requires Stage 1 output first)
- Autoencoder implementation (requires Stage 3 output first)
- MLP Severity Classifier (requires Stages 3+4 and severity labels)

**Can be postponed indefinitely (nice-to-have)**:
- Kafka / Logstash streaming input
- Real-time Slack/Email notifications (n8n stub is functional)
- Streamlit UI (only add after pipeline is stable)

---

## 11. Final Recommendation

### Verdict: Targeted Refactor with New AI Pipeline Components

This is **not a full rewrite** and **not a superficial rename**. It is a **targeted refactor** that preserves the mature infrastructure and replaces the AI learning pipeline.

### Reasoning

**Preserve** (infrastructure is production-grade):
- FastAPI application with auth, middleware, and all endpoints
- AlertManager with cooldown and severity logic
- Prometheus + Grafana observability stack
- Docker + CI/CD pipeline
- 233 automated tests

**Replace** (AI pipeline is architecturally incompatible with requirements):
- Template-ID integer representation -> Word2Vec/FastText float embeddings
- IsolationForest baseline -> Denoising Autoencoder
- GPT-style Transformer (next-token prediction) -> LSTM context encoder
- Rule-based severity classification -> MLP with Softmax

**Add** (required by the document but absent):
- `LogPreprocessor` class
- `LogDataset(torch.utils.data.Dataset)` class
- `SystemBehaviorModel` (LSTM) class
- `AnomalyDetector` (Autoencoder) class
- `SeverityClassifier` (MLP) class
- `ProactiveMonitorEngine` class (consolidation of Pipeline + Engine + Metrics)
- `main.py` clean entrypoint

### Timeline Guidance

The refactor should be executed in the order of the Action Plan (Phases 1-5). Phase 1 and Phase 2 are low-risk structural tasks that unblock Phase 3. Phase 3 is the most complex and should be treated as a new engineering effort — the AI pipeline replacement is equivalent to building Stages 1-5 from scratch with a different architecture.

The existing codebase provides an excellent foundation of infrastructure, tooling, and test coverage. The refactor effort is focused on the learning layers, not on rebuilding the engineering scaffolding. This is a significant advantage: the API contract, the alerting system, the Docker stack, and the CI pipeline can all continue to function during the AI pipeline transition, allowing incremental testing and validation.

**Estimate of impact**:
- Phase 1: Low complexity, low risk
- Phase 2: Low complexity, low risk
- Phase 3: High complexity, high reward — this is the core deliverable
- Phase 4: Medium complexity, enables future UI
- Phase 5: Low complexity, high documentation value

**Final judgment**: The project is ready for a structured refactor. The infrastructure is strong. The AI pipeline needs to be rebuilt from the embedding layer up. The requirements document is achievable with Python-only tools, and the existing codebase provides a solid foundation to build on.

---

*This report was generated by automated analysis of the repository against `PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md`. All class references and file paths are verified against actual repository contents as of 2026-03-06.*
