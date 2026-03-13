# Phase 06 — Severity Classifier Report

## 1. Phase Objective

Implement `SeverityClassifier`, an MLP-based model that receives the latent
representation and reconstruction error produced by `AnomalyDetector` (Phase 5)
and predicts a three-level anomaly severity: **Info**, **Warning**, or **Critical**.

The classifier is self-contained, isolated from all runtime infrastructure, and
ready to be wired into the engine/alert pipeline in a later phase.

---

## 2. What Was Implemented

| Artefact | Description |
|---|---|
| `src/modeling/severity_classifier.py` | Full implementation (replaces Phase 1 stub) |
| `tests/unit/test_severity_classifier.py` | 47-test unit suite, 100 % passing |

The stub file (`# Status: STUB — Phase 1 scaffold only`) was replaced in-place.
No other files were modified.

---

## 3. Input / Output Tensor Contract

### Input

```
latent_vector        : torch.FloatTensor  [batch_size, latent_dim]
reconstruction_error : torch.FloatTensor  [batch_size] or [batch_size, 1]
```

These are concatenated by `SeverityClassifier.build_input()` to produce:

```
features : torch.FloatTensor  [batch_size, latent_dim + 1]
                                         = [batch_size, input_dim]
```

The default `input_dim` is **33** (latent\_dim=32 from `AnomalyDetectorConfig`
default, plus 1 scalar error).

### Output

`forward()` returns **raw logits**:

```
logits : torch.FloatTensor  [batch_size, 3]
```

Softmax is NOT applied inside `forward()` to keep the class compatible with
`nn.CrossEntropyLoss` (which applies log-softmax internally during training).
Callers that need probabilities should call `torch.softmax(logits, dim=-1)`.

---

## 4. MLP Structure

```
Input  [B, input_dim]               (input_dim = latent_dim + 1, default 33)
    |
    v  Linear(input_dim  -> hidden_dim)   default: 33 -> 64
    v  ReLU
    v  Dropout(dropout)                   default: 0.3
    |
    v  Linear(hidden_dim -> hidden_dim)   default: 64 -> 64
    v  ReLU
    v  Dropout(dropout)                   default: 0.3
    |
    v  Linear(hidden_dim -> num_classes)  default: 64 -> 3
    |
logits  [B, 3]
```

The network is stored as `self._mlp` (a single `nn.Sequential` block),
following the pattern of `AnomalyDetector._encoder` / `._decoder`.

---

## 5. Label Mapping

```python
SEVERITY_LABELS = ("info", "warning", "critical")
```

| Index | Label | Meaning |
|---|---|---|
| 0 | `"info"` | Low-risk anomaly; noteworthy but not urgent |
| 1 | `"warning"` | Medium-risk; should be investigated |
| 2 | `"critical"` | High-risk; requires immediate attention |

The mapping is exposed as the module-level constant `SEVERITY_LABELS` so
downstream callers (AlertPolicy, engine) can import it as the single source
of truth.

---

## 6. Predict Behaviour

### `predict(latent_vector, reconstruction_error) -> SeverityOutput`

Convenience method for **single-window** inference:

1. Normalises `latent_vector` to `[1, latent_dim]` (accepts 1-D or 2-D input).
2. Normalises `reconstruction_error` to a `[1]` torch tensor (accepts `float`,
   `np.ndarray`, or `torch.Tensor`).
3. Calls `build_input()` to form the combined feature tensor.
4. Runs `forward()` under `eval()` / `torch.no_grad()`.
5. Applies `torch.softmax` to get probabilities.
6. Returns a `SeverityOutput` named tuple.

### `predict_batch(latent_vectors, reconstruction_errors) -> list[SeverityOutput]`

Batch variant accepting `[B, latent_dim]` and `[B]` / `[B, 1]` tensors.
Returns a `list[SeverityOutput]` of length `B`.

### `SeverityOutput` fields

| Field | Type | Description |
|---|---|---|
| `label` | `str` | `"info"`, `"warning"`, or `"critical"` |
| `class_index` | `int` | 0, 1, or 2 |
| `confidence` | `float` | Softmax probability of the predicted class |
| `probabilities` | `list[float]` | Full 3-class distribution summing to 1.0 |

---

## 7. Save / Load Behaviour

Follows `AnomalyDetector` exactly.

### `save(path)`

```python
torch.save({"state_dict": self.state_dict(), "cfg": self.cfg}, path)
```

- Parent directories are created automatically (`path.parent.mkdir(parents=True, exist_ok=True)`).
- The `SeverityClassifierConfig` dataclass is stored inline in the checkpoint
  (not as a separate JSON file) so a single `.pt` file fully restores the model.

### `load(path, map_location="cpu") -> SeverityClassifier`  (classmethod)

```python
with torch.serialization.safe_globals([SeverityClassifierConfig]):
    ckpt = torch.load(path, map_location=map_location, weights_only=True)
model = cls(ckpt["cfg"])
model.load_state_dict(ckpt["state_dict"])
```

- Uses `safe_globals` to allow `SeverityClassifierConfig` to deserialise
  safely under `weights_only=True` (torch >= 2.0).
- Raises `FileNotFoundError` if the checkpoint does not exist.
- Raises `RuntimeError` if torch is not installed.

---

## 8. Dependencies on Phase 5

`SeverityClassifier` is designed to consume outputs from `AnomalyDetector`
(Phase 5):

| Phase 5 output | Phase 6 input |
|---|---|
| `AEOutput.latent`  — `[B, latent_dim]` | `latent_vector` argument |
| `AEOutput.error`   — `[B]` | `reconstruction_error` argument |

The default `input_dim=33` is derived from:

```
AnomalyDetectorConfig.latent_dim  (default 32)  +  1 (reconstruction_error scalar)
```

If `AnomalyDetectorConfig.latent_dim` is changed, `SeverityClassifierConfig.input_dim`
must be updated to match: `latent_dim + 1`.

---

## 9. Risks / Limitations

| Risk | Notes |
|---|---|
| No training loop | Only the model architecture and persistence are implemented. A training script (with labelled severity data) is required before the model produces meaningful predictions. Until trained, outputs are random. |
| Severity labels must be provided | The classifier is supervised; it requires anomalous windows with ground-truth severity labels for training. These do not currently exist in the dataset pipeline. |
| `input_dim` coupling | `SeverityClassifierConfig.input_dim` must be kept in sync with `AnomalyDetectorConfig.latent_dim`. A mismatch will raise a `RuntimeError` at `forward()` time, which is safe but requires attention during config changes. |
| Untrained model used in existing AlertPolicy | The rule-based `AlertPolicy.classify_severity()` remains the active path in the runtime engine. `SeverityClassifier` is not wired in yet (Phase 7+ work). |
| Softmax temperature | No temperature scaling is implemented. Confidence values from an untrained or lightly-trained model may be overconfident. |

---

## 10. Confirmation — No Unrelated Infrastructure Modified

The following files were **not modified**:

- `src/api/` — FastAPI app, routes, schemas, pipeline
- `src/security/` — auth middleware
- `src/observability/` — metrics, logging
- `src/health/` — health checks
- `src/runtime/` — InferenceEngine, SequenceBuffer, types
- `src/modeling/behavior_model.py` — unchanged
- `src/modeling/anomaly_detector.py` — unchanged
- `src/modeling/transformer/` — unchanged
- `docker-compose.yml`, `Dockerfile`, `.github/workflows/ci.yml` — unchanged
- `prometheus/`, `grafana/` — unchanged
- `requirements.txt` — no new dependencies (torch was already a project dependency)

Only two files were created/modified:

1. **Modified** `src/modeling/severity_classifier.py` — stub replaced with full implementation
2. **Created** `tests/unit/test_severity_classifier.py` — 47-test unit suite

**Test results:** 47/47 new tests pass. Full fast suite (384 tests, `-m "not slow and not integration"`) passes with 0 failures.
