# Phase 07 — Engine Integration Report

## 1. Phase Objective

Implement `ProactiveMonitorEngine` — the top-level orchestrator that connects
the AI pipeline components produced in Phases 2–6 into a single streaming
inference object.

The engine:
- accepts raw log lines from any source (HTTP, file, batch)
- routes them through the full AI pipeline
- produces structured `EngineResult` objects
- remains completely isolated from all existing infrastructure

---

## 2. Engine Architecture

```
ProactiveMonitorEngine
├── _preprocessor         LogPreprocessor       (Phase 2)
├── _behavior_model       SystemBehaviorModel   (Phase 4 / LSTM)
├── _anomaly_detector     AnomalyDetector       (Phase 5 / DAE)
├── _severity_classifier  SeverityClassifier    (Phase 6 / MLP)
├── _buffers              dict[str, _EmbeddingBuffer]   (per stream key)
├── _alert_buffer         deque[dict]           (recent alerts ring buffer)
└── counters              events / windows / anomalies
```

Supporting classes:

| Class | Role |
|---|---|
| `_EmbeddingBuffer` | Rolling `deque(maxlen=window_size)` per stream key; emits a window list when stride interval is met |
| `EngineResult` | Dataclass holding one scored-window result; `to_dict()` for serialisation |

---

## 3. Pipeline Flow Diagram

```
log_line : str
    │
    ▼  LogPreprocessor.process_log()                   [Phase 2]
embedding : np.ndarray  [vec_dim]
    │
    ▼  _EmbeddingBuffer.push()
    │   (returns None until window_size events; then every stride events)
window : list[np.ndarray]  [window_size × vec_dim]
    │
    ▼  np.stack → torch.tensor  →  unsqueeze(0)
x : FloatTensor  [1, window_size, vec_dim]
    │
    ▼  SystemBehaviorModel.forward()                   [Phase 4]
context : FloatTensor  [1, hidden_dim]
    │
    ▼  AnomalyDetector.forward()                       [Phase 5]
AEOutput  (latent [1, latent_dim],  error [1])
    │
    ├─ reconstruction_error = error[0].item()
    ├─ is_anomaly = detector.is_anomaly(reconstruction_error)
    │
    ▼  SeverityClassifier.predict(latent[0], reconstruction_error)  [Phase 6]
SeverityOutput  (label, class_index, confidence, probabilities)
    │
    ▼
EngineResult  {timestamp, service, anomaly_score, reconstruction_error,
               is_anomaly, severity, confidence, probabilities, meta}
```

---

## 4. Component Integration Summary

| Phase | Component | Integration point |
|---|---|---|
| Phase 2 | `LogPreprocessor` | `_embed()` → `process_log()` |
| Phase 3 | `LogDataset` | Not used at runtime (training only); `score_sequence()` accepts pre-built tensors |
| Phase 4 | `SystemBehaviorModel` | `_run_pipeline()` stage 3 |
| Phase 5 | `AnomalyDetector` | `_run_pipeline()` stage 4 |
| Phase 6 | `SeverityClassifier` | `_run_pipeline()` stage 5 |

`LogDataset` is a training utility that is not part of the streaming pipeline.
`score_sequence()` accepts a pre-formed `[window_size, vec_dim]` tensor for
callers that already have embeddings (e.g. offline evaluation).

---

## 5. Error Handling Strategy

Every failure mode is handled without crashing the engine:

| Failure | Behaviour |
|---|---|
| Model file missing at load time | `WARNING` log; model reference stays `None` |
| Model file corrupt / incompatible at load time | `WARNING` log + traceback; model reference stays `None` |
| torch not installed | `WARNING` log; all torch-dependent stages disabled |
| `LogPreprocessor` not loaded | `process_log()` returns `None`; event is silently dropped |
| `SystemBehaviorModel` unavailable | `_run_pipeline()` returns `_fallback_result()` |
| `AnomalyDetector` unavailable | `_run_pipeline()` returns `_fallback_result()` |
| `SeverityClassifier` unavailable | Result uses `severity="info", confidence=0.0` |
| Unexpected exception in `_run_pipeline()` | `ERROR` log + traceback; `_fallback_result()` returned |

`_fallback_result()` always returns a valid `EngineResult` with:
```python
anomaly_score=0.0, is_anomaly=False, severity="info", confidence=0.0
```

---

## 6. Model Loading Logic

`initialize_models()` (aliased as `load_models()` for backward compat):

```
models_dir/
  word2vec.model          → LogPreprocessor.load()        (gensim)
  behavior_model.pt       → SystemBehaviorModel.load()    (torch safe_globals)
  anomaly_detector.pt     → AnomalyDetector.load()        (torch safe_globals)
  severity_classifier.pt  → SeverityClassifier.load()     (torch safe_globals)
```

Each loader:
1. Checks file existence; warns and returns `None` if absent.
2. Calls the class's `load()` classmethod inside `try/except`.
3. Calls `.eval()` on the loaded model.
4. Logs success with key hyperparameters.

Default `models_dir` = `<project_root>/models`.

---

## 7. Dependencies on Phases 2–6

| Dependency | Reason |
|---|---|
| `LogPreprocessor` (Phase 2) | Converts raw log strings to `[vec_dim]` float vectors |
| `LogDataset` (Phase 3) | Not used at runtime; `score_sequence()` is the offline interface |
| `SystemBehaviorModel` / `BehaviorModelConfig` (Phase 4) | Produces `[hidden_dim]` context vector from window |
| `AnomalyDetector` / `AnomalyDetectorConfig` (Phase 5) | Reconstruction error + latent vector; `is_anomaly()` threshold |
| `SeverityClassifier` / `SEVERITY_LABELS` (Phase 6) | Severity label + confidence from latent + error |

Dimension coupling:
```
LogPreprocessor.vec_dim          == BehaviorModelConfig.input_dim
BehaviorModelConfig.hidden_dim   == AnomalyDetectorConfig.input_dim
AnomalyDetectorConfig.latent_dim == SeverityClassifierConfig.input_dim - 1
```

---

## 8. Rolling Buffer Design

`_EmbeddingBuffer` per stream key:

- Uses `deque(maxlen=window_size)` — auto-drops oldest vector when full.
- **Emit condition**: `total_events >= window_size AND (total_events - window_size) % stride == 0`
  - First window emitted at event #window\_size.
  - Subsequent windows emitted every `stride` events.
- Stream keys are held in an insertion-ordered dict; oldest key is evicted
  when `max_stream_keys` is reached (LRU-style cap).

---

## 9. Risks / Limitations

| Risk | Notes |
|---|---|
| No trained models in repository | All Phase 2–6 models are scaffold implementations without training scripts or training data. At runtime, `initialize_models()` will warn about every missing file and the engine will return `_fallback_result()` for every window. |
| Dimension coupling across phases | If `AnomalyDetectorConfig.latent_dim` is changed, `SeverityClassifierConfig.input_dim` must also be updated to `latent_dim + 1`. The engine does not auto-detect this mismatch at load time; it will raise at `_run_pipeline()` time and fall back gracefully. |
| No training loop | The engine cannot train models. A separate training pipeline (data ingestion → training scripts) is required before the MLP models produce meaningful outputs. |
| `LogPreprocessor` gensim dependency | If gensim is not installed, `LogPreprocessor.load()` raises `ImportError`. The engine's `_load_preprocessor()` catches this and disables the embedding stage. |
| Not wired to FastAPI | The engine is completely isolated. It does NOT replace `Pipeline` (src/api/pipeline.py) yet. That integration is deferred to a future phase. |
| Confidence calibration | `SeverityClassifier` outputs are raw softmax from an untrained MLP, which may be overconfident or meaningless until trained. |

---

## 10. Confirmation — No Unrelated Infrastructure Modified

The following were **not modified**:

- `src/api/` — FastAPI app, routes, schemas, pipeline
- `src/runtime/` — InferenceEngine, SequenceBuffer, types, RiskResult
- `src/alerts/` — AlertManager, AlertPolicy, models
- `src/security/` — auth middleware
- `src/observability/` — metrics, logging
- `src/health/` — health checks
- `src/modeling/behavior_model.py` — unchanged
- `src/modeling/anomaly_detector.py` — unchanged
- `src/modeling/severity_classifier.py` — unchanged
- `src/preprocessing/log_preprocessor.py` — unchanged
- `docker-compose.yml`, `Dockerfile`, `.github/workflows/ci.yml` — unchanged
- `prometheus/`, `grafana/` — unchanged
- `requirements.txt` — no new dependencies

Files created / modified:

1. **Modified** `src/engine/proactive_engine.py` — stub replaced with full implementation
2. **Modified** `src/engine/__init__.py` — exports `ProactiveMonitorEngine`, `EngineResult`
3. **Created** `tests/unit/test_proactive_engine.py` — 65-test unit suite

**Test results:** 65/65 new tests pass. Full fast suite (449 tests,
`-m "not slow and not integration"`) passes with 0 failures.
