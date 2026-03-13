# PHASE_05_ANOMALY_DETECTOR_REPORT.md
## Predictive Log Anomaly Engine — Phase 5 Refactor Progress Report

**Phase:** 5 — Anomaly Detection Engine
**Status:** Complete
**Date:** 2026-03-08
**Scope:** Full implementation of `AnomalyDetector` and `AnomalyDetectorConfig` at `src/modeling/anomaly_detector.py`

---

## 1. Phase Objective

Phase 5 implements the anomaly detection stage: a Denoising Autoencoder that consumes context vectors from `SystemBehaviorModel` (Phase 4) and produces a reconstruction error as an anomaly score.

The concrete goal is an `nn.Module` that:
- compresses context vectors to a latent representation via an encoder
- reconstructs the original context vector via a decoder
- measures per-sample reconstruction error as the anomaly signal
- supports percentile-based threshold calibration from normal-sequence validation errors
- preserves the calibrated threshold across save/load cycles

---

## 2. What Was Implemented

### `src/modeling/anomaly_detector.py`

Phase 5 replaced all `NotImplementedError` stubs with a full implementation. Three new objects were added:

| Symbol | Type | Description |
|---|---|---|
| `AEOutput` | `NamedTuple` | Named return type for `forward()`: `(latent, reconstructed, error)` |
| `AnomalyDetectorConfig` | `@dataclass` | JSON-serialisable hyperparameter container |
| `AnomalyDetector` | `nn.Module` | Denoising autoencoder with calibration and persistence |

#### `AnomalyDetectorConfig` fields

| Field | Default | Description |
|---|---|---|
| `input_dim` | 128 | Context vector size; must match `BehaviorModelConfig.hidden_dim` |
| `latent_dim` | 32 | Bottleneck dimension (compression ratio with defaults: 4:1) |
| `intermediate_dim` | 64 | Hidden layer size in encoder and decoder |
| `dropout` | 0.1 | Dropout probability applied after first linear layer in each block |
| `noise_std` | 0.05 | Gaussian noise std for denoising; `0.0` = plain autoencoder |

#### `AnomalyDetector` members

| Member | Description |
|---|---|
| `__init__(cfg)` | Builds encoder and decoder `nn.Sequential` blocks |
| `forward(x)` | Runs encoder → latent → decoder; returns `AEOutput` |
| `reconstruction_error(original, reconstructed)` | Standalone per-sample MSE helper |
| `fit_threshold(normal_errors, percentile)` | Calibrates threshold from normal-sequence validation errors |
| `is_anomaly(error)` | Returns `True` if scalar error exceeds threshold |
| `is_calibrated` | Property: `True` after `fit_threshold()` has been called |
| `score(context_vector)` | Inference convenience: returns `np.ndarray` of per-sample errors |
| `save(path)` | Saves `{state_dict, cfg, threshold, calibrated}` checkpoint |
| `AnomalyDetector.load(path, map_location)` | Restores weights, config, threshold, calibration flag |

No other existing file was modified.

---

## 3. Input / Output Tensor Contract

### Input

```
context_vector: torch.FloatTensor [batch_size, input_dim]
```

Produced by `SystemBehaviorModel.forward()` (Phase 4). Must be exactly 2-D.

### Output (`AEOutput` NamedTuple)

| Field | Shape | Description |
|---|---|---|
| `latent` | `[batch_size, latent_dim]` | Compressed bottleneck representation |
| `reconstructed` | `[batch_size, input_dim]` | Decoder output |
| `error` | `[batch_size]` | Per-sample MSE between clean input and `reconstructed` |

```python
out = detector(context)      # context: [B, 128]
out.latent.shape             # [B, 32]
out.reconstructed.shape      # [B, 128]
out.error.shape              # [B]     — anomaly scores
```

The `AEOutput` NamedTuple was chosen over a plain tuple to prevent positional confusion when downstream code (Phase 6 `SeverityClassifier`) accesses both `latent` and `error` by name.

---

## 4. Encoder / Decoder Structure

### Encoder: `input_dim → intermediate_dim → latent_dim`

```python
nn.Sequential(
    nn.Linear(input_dim,       intermediate_dim),  # 128 → 64
    nn.ReLU(),
    nn.Dropout(dropout),
    nn.Linear(intermediate_dim, latent_dim),        # 64  → 32
)
```

- No activation on the final encoder layer — the latent space is unconstrained, which suits continuous float vectors
- Dropout regularises the compression path to prevent overfitting to training noise

### Decoder: `latent_dim → intermediate_dim → input_dim`

```python
nn.Sequential(
    nn.Linear(latent_dim,       intermediate_dim),  # 32  → 64
    nn.ReLU(),
    nn.Dropout(dropout),
    nn.Linear(intermediate_dim, input_dim),         # 64  → 128
)
```

- No activation on the output layer — reconstruction must be unbounded to match the original context vectors (which can be negative)
- Symmetric with the encoder in depth and width

### Default compression path

```
[128] → Linear → ReLU → Dropout → [64] → Linear → [32]  (encoder)
[32]  → Linear → ReLU → Dropout → [64] → Linear → [128] (decoder)
```

Compression ratio: 4:1. The bottleneck forces the model to learn a compact normal-behaviour representation, making reconstruction error a discriminative anomaly signal.

---

## 5. Latent Representation Design

The latent vector `[batch, latent_dim]` is the output of the encoder's final linear layer with **no activation**. This is intentional:

- ReLU at the bottleneck would truncate negative directions, reducing representational capacity
- The latent space will be consumed by `SeverityClassifier` (Phase 6), which expects a continuous float vector

The latent vector is accessible via `AEOutput.latent` for both training loss inspection and the Phase 6 input:

```python
# Phase 6 input (SeverityClassifier stub):
# features = cat(latent [latent_dim], error.unsqueeze(-1) [1]) → [latent_dim + 1]
features = torch.cat([out.latent, out.error.unsqueeze(-1)], dim=-1)
```

---

## 6. Reconstruction Error Behaviour

### Per-sample MSE

```python
error = ((x - reconstructed) ** 2).mean(dim=-1)  # [batch]
```

Mean is taken over the `input_dim` dimension, producing one scalar per sequence window.

**Key property:** the error is always computed against the **clean** input `x`, not the noisy `x_enc` used by the encoder during training. This is the defining property of a denoising autoencoder:

- Training: `encode(x + noise) → latent → decode(latent) → loss = MSE(x_clean, reconstructed)`
- Inference: `encode(x) → latent → decode(latent) → error = MSE(x, reconstructed)`

The effect: the decoder must learn to map any reasonable encoding back to the true clean signal, making it more robust to input perturbations.

### Threshold calibration

`fit_threshold(normal_errors, percentile=95.0)` sets:

```python
self.threshold = float(np.percentile(normal_errors, percentile))
```

With the default percentile of 95, up to 5% of normal-sequence validation windows are allowed to exceed the threshold (controlled false-positive rate). This is the same convention used by `AnomalyScorer` in the existing transformer baseline.

`is_anomaly(error: float)` returns `error > self.threshold` (strict inequality).

The threshold and calibration flag are persisted in the checkpoint so calibration survives across save/load cycles.

---

## 7. Save / Load Behaviour

The checkpoint format mirrors `SystemBehaviorModel` and `NextTokenTransformerModel` exactly:

### `save(path)`

```python
torch.save(
    {
        "state_dict": self.state_dict(),
        "cfg":        self.cfg,
        "threshold":  self.threshold,
        "calibrated": self._calibrated,
    },
    path,
)
```

- Saves full `nn.Module` state dict (encoder + decoder weights)
- Saves config so the model can be reconstructed without external configuration
- Saves `threshold` and `calibrated` so threshold calibration survives reload

### `AnomalyDetector.load(path, map_location="cpu")`

```python
with torch.serialization.safe_globals([AnomalyDetectorConfig]):
    ckpt = torch.load(path, map_location=map_location, weights_only=True)
model = cls(ckpt["cfg"])
model.load_state_dict(ckpt["state_dict"])
model.threshold = ckpt.get("threshold", 0.0)
model._calibrated = ckpt.get("calibrated", False)
```

- `weights_only=True` required by PyTorch >= 2.0 for safe loading
- `safe_globals([AnomalyDetectorConfig])` allows the config dataclass to be deserialised safely
- `ckpt.get("threshold", 0.0)` provides backwards compatibility if checkpoint was saved before calibration was added

---

## 8. Dependencies on Phase 4

`AnomalyDetector` is designed to consume `SystemBehaviorModel.forward()` output directly:

```
SystemBehaviorModel.forward(x)
    → context: FloatTensor [batch, hidden_dim]
        |
AnomalyDetector.forward(context)
    → AEOutput(latent, reconstructed, error)
```

**Dimension alignment requirement:**
- `AnomalyDetectorConfig.input_dim` must equal `BehaviorModelConfig.hidden_dim`
- Enforced at runtime by the 2-D shape check and `input_dim` check in `forward()`
- Verified end-to-end in `TestPipelineIntegration.test_behavior_model_to_anomaly_detector`

---

## 9. Test Suite

63 new unit tests were added at `tests/unit/test_anomaly_detector.py`.

### Test classes

| Class | Tests | Coverage |
|---|---|---|
| `TestAnomalyDetectorConfig` | 4 | Defaults, custom values, JSON save/load, JSON key set |
| `TestConstruction` | 8 | Default config, explicit config, encoder/decoder exist, `nn.Module`, uncalibrated default, Sequential type |
| `TestAEOutput` | 2 | Named field access, positional unpack |
| `TestForwardShapes` | 7 | Latent shape, reconstructed shape, error shape, dtype, non-negative, batch=1, latent dtype |
| `TestForwardValidation` | 3 | 1-D input, 3-D input, wrong `input_dim` |
| `TestDenoising` | 4 | Eval mode deterministic, train mode noise differs, noise_std=0 deterministic, error vs clean input |
| `TestReconstructionError` | 4 | Shape, zero for identical, positive for different, MSE value |
| `TestFitThreshold` | 10 | Sets threshold, marks calibrated, list/numpy/tensor inputs, empty raises, percentile validation, p100, value correctness |
| `TestIsAnomaly` | 4 | Below threshold, above threshold, exactly at threshold, uncalibrated warning |
| `TestScore` | 4 | numpy float32 return, shape, non-negative, switches to eval |
| `TestPersistence` | 7 | Creates file, parent dirs, restores config, restores weights, restores threshold+calibrated, uncalibrated preserved, missing file |
| `TestTorchAbsentGuard` | 4 | `forward`, `save`, `load`, `reconstruction_error` raise `RuntimeError` |
| `TestPipelineIntegration` | 2 | `LogDataset → BehaviorModel → AnomalyDetector` end-to-end; `fit_threshold` from pipeline output |

### Test suite results

```
393 passed, 22 deselected in 8.44s
```

- **393 tests passed** (330 pre-Phase 5 + 63 new Phase 5 tests)
- **22 deselected** (slow/model-dependent tests, unchanged)
- **0 failures, 0 errors**

---

## 10. Risks and Limitations

| Risk | Severity | Mitigation |
|---|---|---|
| Autoencoder trained on a mix of normal and anomalous samples will not learn a useful threshold | High | Training must use **normal sequences only** (label=0). This is a training-time constraint, not enforced by the class. Documented clearly in the class docstring. |
| `threshold = 0.0` default flags every window as anomalous | Medium | `is_calibrated` property and `logger.warning` in `is_anomaly()` guard against uncalibrated use. Phase 7 integration must call `fit_threshold()` after training. |
| Gaussian noise std of 0.05 is a reasonable default but not tuned | Low | `noise_std` is a config parameter; it can be set to 0.0 for a plain autoencoder or tuned during Phase 7 training experiments. |
| Reconstruction error is MSE averaged over `input_dim` | Low | Alternative: sum instead of mean. Mean normalises across different `input_dim` sizes; sum is more sensitive. Phase 7 can evaluate both. |
| No `nn.BatchNorm` between layers | Low | BatchNorm may improve training stability for deeper autoencoders. Deferred to Phase 7 if training experiments show instability. |
| Latent space has no regularisation (no KL divergence, no variational component) | Low | A standard Denoising Autoencoder (not VAE) is specified in the architecture. The noise injection provides sufficient regularisation for the anomaly detection use case. |

---

## 11. Infrastructure Safety

The following was verified after Phase 5:

| Component | Status |
|---|---|
| `src/api/` | Unchanged |
| `src/runtime/` | Unchanged |
| `src/alerts/` | Unchanged |
| `src/observability/` | Unchanged |
| `src/modeling/baseline/` | Unchanged — IsolationForest fallback active |
| `src/modeling/transformer/` | Unchanged — Transformer fallback active |
| `src/preprocessing/` | Unchanged |
| `src/dataset/` | Unchanged |
| `src/modeling/behavior_model.py` | Unchanged |
| `models/baseline.pkl` | Unchanged |
| `models/transformer.pt` | Unchanged |
| `Dockerfile`, `docker-compose.yml` | Unchanged |
| `.github/workflows/ci.yml` | Unchanged |
| `requirements.txt` | Unchanged |
| Existing tests (330) | All passing |

**No existing module was modified.** `AnomalyDetector` is not imported by any existing module and has no effect on the production runtime path until Phase 7.

---

## 12. Phase Boundary

Phase 5 is complete. The following are deferred to later phases:

| Deferred item | Phase |
|---|---|
| `SeverityClassifier` (MLP: latent + error → Info/Warning/Critical) | Phase 6 |
| `ProactiveMonitorEngine` (end-to-end orchestrator) | Phase 7 |
| Training the autoencoder on normal-only sequences | Phase 7 |
| Threshold calibration on validation set during training | Phase 7 |
| Wiring `AnomalyDetector` into the live `/ingest` pipeline | Phase 7 |

Phase 5 is complete. The repository is ready for Phase 6 (Severity Classification — `SeverityClassifier` MLP implementation).
