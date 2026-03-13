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
