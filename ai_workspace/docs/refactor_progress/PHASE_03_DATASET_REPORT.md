# PHASE_03_DATASET_REPORT.md
## Predictive Log Anomaly Engine — Phase 3 Refactor Progress Report

**Phase:** 3 — Sequence Dataset Pipeline
**Status:** Complete
**Date:** 2026-03-08
**Scope:** Full implementation of `LogDataset` at `src/dataset/log_dataset.py`

---

## 1. Phase Objective

Phase 3 implements the sequence dataset layer: the bridge between the NLP embedding output of Phase 2 (`LogPreprocessor`) and the LSTM model input of Phase 4 (`SystemBehaviorModel`).

The concrete goal is to produce a `torch.utils.data.Dataset` that:
- accepts per-log-line float embedding vectors (produced by `LogPreprocessor`)
- builds sliding windows over the sequence of embeddings
- returns `(FloatTensor[window_size, vec_dim], label)` items consumable by `DataLoader`
- produces batches of shape `[batch_size, window_size, vec_dim]` ready for LSTM training

---

## 2. What Was Implemented

### `src/dataset/log_dataset.py` — `LogDataset`

Phase 3 replaced all `NotImplementedError` stubs with a working implementation. The class now provides:

| Member | Type | Description |
|---|---|---|
| `__init__` | Constructor | Accepts embeddings, optional labels, window_size, stride; builds window index table |
| `__len__` | `int` | Number of sliding windows in the dataset |
| `__getitem__` | `(FloatTensor, int)` | Returns window tensor and label for index `idx` |
| `_build_windows` | Internal | Computes `(start, end, label)` index table at construction time |
| `vec_dim` | `int` | Embedding dimensionality, inferred from the first vector |
| `has_labels` | `bool` | True when per-line labels were supplied |
| `num_windows` | `int` | Alias for `len(self)` |
| `label_counts` | `dict` | `{"normal": N, "anomaly": N}` — class balance summary |
| `from_csv` | Class method | Load a log CSV, embed via `LogPreprocessor`, return `LogDataset` |

### `src/dataset/__init__.py`

Updated to export `LogDataset` directly:

```python
from .log_dataset import LogDataset
__all__ = ["LogDataset"]
```

No other existing file was modified.

---

## 3. Dataset Input / Output Contract

### Input

| Parameter | Type | Description |
|---|---|---|
| `embeddings` | `List[np.ndarray]` | One 1-D float32 vector per log line; all must share the same shape `(vec_dim,)` |
| `labels` | `Optional[List[int]]` | Per-line integer labels aligned to `embeddings`; `None` if unlabeled |
| `window_size` | `int` | Consecutive lines per window (default 20) |
| `stride` | `int` | Step between window start positions (default 1) |

### Output (per `__getitem__` call)

| Field | Type | Shape | Description |
|---|---|---|---|
| `tensor` | `torch.FloatTensor` | `[window_size, vec_dim]` | Stacked embedding vectors for the window |
| `label` | `int` | scalar | `0` = all-normal window, `1` = at least one anomalous log line in window |

### Batch Output (via DataLoader)

```python
loader = DataLoader(dataset, batch_size=32, shuffle=True)
# Each batch:
#   tensors.shape == (32, window_size, vec_dim)   — matches LSTM expected input
#   labels.shape  == (32,)
```

---

## 4. Sliding Window Logic

### Design source

The window-building loop is directly adapted from `src/sequencing/builders.py` (`SlidingWindowSequenceBuilder.build()`). That class uses the same `(start, stride, window)` pattern over token ID sequences. `LogDataset._build_windows()` applies the identical arithmetic over float embedding vectors.

### Algorithm

```python
for start in range(0, n, self.stride):
    end = start + self.window_size
    if end > n:
        break          # discard incomplete trailing window
    label = int(max(labels[start:end])) if labels else 0
    windows.append((start, end, label))
```

**Key properties:**
- Windows are built eagerly at construction time and stored as `(start, end, label)` index tuples
- No embedding data is duplicated in memory; `__getitem__` reads from `self.embeddings` at access time via `np.stack(embeddings[start:end])`
- Trailing incomplete windows are discarded to guarantee that every item returned by `__getitem__` has exactly `window_size` rows (required for LSTM fixed-length input)

### Window count formula

For `n` embeddings, `window_size` W, and `stride` S:

```
num_windows = floor((n - W) / S) + 1   if n >= W
            = 0                         if n < W
```

### Label aggregation

Window label = `max(labels[start:end])`. A window is labelled anomalous (`1`) if any constituent log line is labelled `1`. This is the same strategy used by `SlidingWindowSequenceBuilder` (line 68: `max(labels[start:end])`).

---

## 5. Tensor Shapes

### Single item

| Stage | Shape | Notes |
|---|---|---|
| Raw log message | `str` | Input to `LogPreprocessor.process_log()` |
| Log-line embedding | `(vec_dim,)` = `(100,)` | Output of `LogPreprocessor` |
| Stacked window | `(window_size, vec_dim)` = `(20, 100)` | `np.stack` of W embeddings |
| Tensor | `torch.FloatTensor[window_size, vec_dim]` | Output of `LogDataset.__getitem__` |

### Batched

| Stage | Shape |
|---|---|
| DataLoader batch | `[batch_size, window_size, vec_dim]` e.g. `[32, 20, 100]` |
| LSTM expected input | `[batch_size, seq_len, input_size]` = `[32, 20, 100]` |

The batch shape matches the PyTorch LSTM `input` parameter convention `(batch, seq, feature)` when `batch_first=True` is set on the LSTM layer in Phase 4.

---

## 6. Dependencies on Phase 2

`LogDataset` consumes the output of `LogPreprocessor` in two ways:

### Direct consumption (inference path)

```python
vector = preprocessor.process_log(raw_message)   # np.ndarray (vec_dim,)
# -> stored in embeddings list passed to LogDataset
```

### `from_csv` factory

```python
ds = LogDataset.from_csv(
    csv_path="data/logs.csv",
    preprocessor=trained_preprocessor,
    window_size=20,
    stride=1,
)
```

The factory calls `preprocessor.process_log(msg)` for every row in the CSV. It requires `preprocessor.is_trained == True` and raises `RuntimeError` otherwise, enforcing the Phase 2 → Phase 3 dependency explicitly.

**Contract:** `LogDataset` does not call `clean()` or `tokenize()` directly. It consumes only the final embedding output of `process_log()`. This keeps the boundary clean: Phase 2 owns NLP, Phase 3 owns tensor preparation.

---

## 7. Test Suite

42 new unit tests were added at `tests/unit/test_log_dataset.py`.

### Test classes

| Class | Tests | Coverage |
|---|---|---|
| `TestConstruction` | 5 | Valid inputs, vec_dim/window_size/stride stored |
| `TestValidation` | 6 | Empty embeddings, window<1, stride<1, shape mismatch, labels length mismatch |
| `TestLen` | 6 | Window count for stride=1, stride=W, stride>W, window=n, window>n, no labels |
| `TestGetItem` | 10 | Tensor shape, dtype, label type, all-normal, anomaly in/outside window, IndexError |
| `TestLabelPropagation` | 2 | max-label rule, no-label defaults to 0 |
| `TestProperties` | 5 | has_labels, num_windows, label_counts |
| `TestTorchAbsentGuard` | 1 | RuntimeError when torch absent (mocked) |
| `TestDataLoaderIntegration` | 1 | Batch shape `[4, 5, 16]` via DataLoader |
| `TestFromCsv` | 6 | Valid load, tensor shape, no-label CSV, missing file, untrained preprocessor, missing column |

### Test suite results

```
297 passed, 22 deselected in 17.70s
```

- **297 tests passed** (255 pre-Phase 3 + 42 new Phase 3 tests)
- **22 deselected** (slow/model-dependent tests, unchanged)
- **0 failures, 0 errors**

---

## 8. Risks and Limitations

| Risk | Severity | Mitigation |
|---|---|---|
| Trailing incomplete windows are silently discarded | Low | Documented clearly. If `n < window_size` the dataset is empty with `len(ds) == 0`. Callers should check `len(ds) > 0` before training. |
| Zero-vector embeddings for OOV-heavy log lines | Medium | Inherited from Phase 2. Windows of all-zero vectors produce valid tensors but may confuse the LSTM. No mitigation in Phase 3 — deferred to Phase 4 evaluation. |
| Large datasets hold all embeddings in memory | Medium | `_build_windows` stores only index tuples, not stacked arrays. Embedding data is held once in `self.embeddings`. For very large datasets a memory-mapped approach may be needed in Phase 4, but is not required now. |
| `from_csv` iterates all rows with `process_log` in Python | Medium | Acceptable for training-time preprocessing. Real-time inference uses `LogPreprocessor.process_log` directly, not the batch factory. |
| No shuffle in `LogDataset` itself | Low | Shuffle is delegated to `DataLoader(shuffle=True)` — the standard PyTorch pattern. |

---

## 9. Infrastructure Safety

The following was verified after Phase 3:

| Component | Status |
|---|---|
| `src/api/` | Unchanged |
| `src/runtime/` | Unchanged |
| `src/alerts/` | Unchanged |
| `src/observability/` | Unchanged |
| `src/sequencing/` | Unchanged (logic reused, not modified) |
| `src/preprocessing/` | Unchanged |
| `models/baseline.pkl` | Unchanged — fallback path active |
| `models/transformer.pt` | Unchanged — fallback path active |
| `Dockerfile`, `docker-compose.yml` | Unchanged |
| `.github/workflows/ci.yml` | Unchanged |
| `requirements.txt` | Unchanged (torch already present) |
| Existing tests (255) | All passing |

**No existing module was modified.** `LogDataset` is not imported by any existing module and has no effect on the production runtime path until Phase 7.

---

## 10. Phase Boundary

Phase 3 is complete. The following are deferred to later phases:

| Deferred item | Phase |
|---|---|
| `SystemBehaviorModel` (LSTM encoder) | Phase 4 |
| `AnomalyDetector` (Denoising Autoencoder) | Phase 5 |
| `SeverityClassifier` (MLP severity predictor) | Phase 6 |
| `ProactiveMonitorEngine` (end-to-end orchestrator) | Phase 7 |
| Wiring `LogDataset` into the live `/ingest` training pipeline | Phase 7 |

Phase 3 is complete. The repository is ready for Phase 4 (System Behavior Modeling — `SystemBehaviorModel` LSTM implementation).
