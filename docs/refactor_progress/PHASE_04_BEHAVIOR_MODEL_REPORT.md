# PHASE_04_BEHAVIOR_MODEL_REPORT.md
## Predictive Log Anomaly Engine — Phase 4 Refactor Progress Report

**Phase:** 4 — System Behavior Modeling
**Status:** Complete
**Date:** 2026-03-08
**Scope:** Full implementation of `SystemBehaviorModel` and `BehaviorModelConfig` at `src/modeling/behavior_model.py`

---

## 1. Phase Objective

Phase 4 implements the sequence behavior model: the LSTM that consumes batched log-window tensors from `LogDataset` (Phase 3) and produces a single context vector per window. This context vector is the input to `AnomalyDetector` in Phase 5.

The concrete goal is a `nn.Module` subclass that:
- accepts input of shape `[batch_size, seq_len, input_dim]`
- runs a stacked LSTM over the sequence
- extracts the final hidden state as a behavioral summary
- always outputs `[batch_size, hidden_dim]` regardless of bidirectionality
- saves and loads checkpoints in a format compatible with the rest of the repository

---

## 2. What Was Implemented

### `src/modeling/behavior_model.py`

Phase 4 replaced all `NotImplementedError` stubs with a full implementation. Two classes were added:

| Class | Description |
|---|---|
| `BehaviorModelConfig` | JSON-serialisable `@dataclass` holding all LSTM hyperparameters |
| `SystemBehaviorModel` | `nn.Module` LSTM with projection layer and safe checkpoint persistence |

#### `BehaviorModelConfig` members

| Field | Default | Description |
|---|---|---|
| `input_dim` | 100 | Input vector size; must match `LogPreprocessor.vec_dim` |
| `hidden_dim` | 128 | LSTM hidden state size and final output dimensionality |
| `num_layers` | 2 | Number of stacked LSTM layers |
| `dropout` | 0.2 | Dropout between LSTM layers (forced to 0.0 when `num_layers == 1`) |
| `bidirectional` | False | Enables BiLSTM; output is projected back to `hidden_dim` |
| `save(path)` | — | Serialises config to JSON |
| `BehaviorModelConfig.load(path)` | — | Deserialises config from JSON |

#### `SystemBehaviorModel` members

| Member | Description |
|---|---|
| `__init__(cfg)` | Builds LSTM and optional projection layer |
| `forward(x)` | Runs LSTM; returns context vector `[batch, hidden_dim]` |
| `save(path)` | Saves `{state_dict, cfg}` checkpoint via `torch.save` |
| `SystemBehaviorModel.load(path, map_location)` | Loads checkpoint; restores config and weights |
| `input_dim`, `hidden_dim`, `num_layers`, `bidirectional` | Direct attribute access to config fields |

No other existing file was modified.

---

## 3. Input / Output Tensor Contract

### Input

| Dimension | Size | Source |
|---|---|---|
| `batch_size` | variable | `DataLoader` batch |
| `seq_len` | `window_size` | `LogDataset.window_size` (default 20) |
| `input_dim` | `vec_dim` | `LogPreprocessor.vec_dim` (default 100) |

```
x: torch.FloatTensor [batch_size, seq_len, input_dim]
```

### Output

```
context: torch.FloatTensor [batch_size, hidden_dim]
```

The output shape is always `[batch_size, hidden_dim]` regardless of whether `bidirectional=True` or `False`. The projection layer (described below) enforces this contract.

### Example

```python
cfg  = BehaviorModelConfig(input_dim=100, hidden_dim=128)
model = SystemBehaviorModel(cfg)
x     = torch.randn(32, 20, 100)   # [batch=32, seq=20, vec=100]
ctx   = model(x)                   # [32, 128]
```

---

## 4. LSTM Architecture

### Network structure

```
Input  [B, T, input_dim]
    |
    v  nn.LSTM(batch_first=True, bidirectional=False)
h_n  [num_layers, B, hidden_dim]
    |
    | h_n[-1] — final layer hidden state
    v
context  [B, hidden_dim]
```

For bidirectional mode:

```
Input  [B, T, input_dim]
    |
    v  nn.LSTM(batch_first=True, bidirectional=True)
h_n  [num_layers * 2, B, hidden_dim]
    |
    | cat(h_n[-2], h_n[-1]) — forward + backward final states
    v
h    [B, 2 * hidden_dim]
    |
    v  nn.Linear(2 * hidden_dim → hidden_dim)
context  [B, hidden_dim]
```

### Why a projection layer?

The projection layer (`nn.Linear`) is added only when `bidirectional=True`. Its purpose:
- The BiLSTM produces a concatenation of forward/backward final hidden states of shape `[B, 2 * hidden_dim]`
- Without projection, downstream phases would need to branch on bidirectionality
- With projection, the output is always `[B, hidden_dim]` — the contract is stable regardless of config

For unidirectional mode (`_proj = None`), the LSTM final hidden state `h_n[-1]` is already `[B, hidden_dim]` and no projection is needed.

### `batch_first=True`

The LSTM is constructed with `batch_first=True` so the batch dimension is first, matching the standard PyTorch convention and the `DataLoader` output from Phase 3:
```
DataLoader batch: [batch, seq, features]  →  LSTM input
```

### Dropout note

PyTorch's `nn.LSTM` requires `dropout > 0` only when `num_layers > 1` (it is applied between layers). When `num_layers == 1`, the dropout argument is silently forced to `0.0` to prevent a PyTorch warning.

---

## 5. Configurable Parameters

All hyperparameters are held in `BehaviorModelConfig`. The dataclass is JSON-serialisable via `save(path)` / `load(path)`, mirroring `TransformerConfig` exactly.

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `input_dim` | `int` | 100 | Must match `LogPreprocessor.vec_dim` |
| `hidden_dim` | `int` | 128 | LSTM hidden state and output dimension |
| `num_layers` | `int` | 2 | Stacked LSTM depth; 1 is valid (dropout forced to 0) |
| `dropout` | `float` | 0.2 | Applied between layers when `num_layers > 1` |
| `bidirectional` | `bool` | False | Safe default; BiLSTM adds a projection layer |

### Config JSON format

```json
{
  "input_dim": 100,
  "hidden_dim": 128,
  "num_layers": 2,
  "dropout": 0.2,
  "bidirectional": false
}
```

---

## 6. Save / Load Behaviour

The checkpoint format mirrors `NextTokenTransformerModel` exactly:

### `save(path)`

```python
torch.save({"state_dict": self.state_dict(), "cfg": self.cfg}, path)
```

- Stores the full `nn.Module` state dict (LSTM weights, projection weights if bidirectional)
- Stores the `BehaviorModelConfig` dataclass so the model can be reconstructed without external config
- Parent directories are created automatically

### `SystemBehaviorModel.load(path, map_location="cpu")`

```python
with torch.serialization.safe_globals([BehaviorModelConfig]):
    ckpt = torch.load(path, map_location=map_location, weights_only=True)
model = cls(ckpt["cfg"])
model.load_state_dict(ckpt["state_dict"])
```

- Uses `weights_only=True` (required by PyTorch >= 2.0 for safe loading)
- Uses `safe_globals([BehaviorModelConfig])` to allow the config dataclass to be deserialised safely (same pattern as `NextTokenTransformerModel.load`)
- Returns a new `SystemBehaviorModel` instance with weights and config restored

### Round-trip guarantee

```python
model.eval()
out1 = model(x)
model.save("models/behavior_model.pt")
model2 = SystemBehaviorModel.load("models/behavior_model.pt")
model2.eval()
out2 = model2(x)
# out1 == out2 to float32 precision
```

---

## 7. Dependencies on Phase 3

`SystemBehaviorModel` is designed to consume `LogDataset` / `DataLoader` output directly:

```
LogDataset.__getitem__ → FloatTensor[window_size, vec_dim]
    |
DataLoader             → FloatTensor[batch_size, window_size, vec_dim]
    |
SystemBehaviorModel.forward → FloatTensor[batch_size, hidden_dim]
```

The tensor shape contract is verified end-to-end in `TestPipelineIntegration`: a `LogDataset` backed by synthetic embeddings is wrapped in a `DataLoader`, the first batch is passed through `SystemBehaviorModel`, and the output shape is asserted.

**Dimension alignment requirement:**
- `LogPreprocessor.vec_dim` must equal `BehaviorModelConfig.input_dim`
- `LogDataset.window_size` is the `seq_len` dimension and can be any value ≥ 1
- Enforced at runtime by the input-dimension check in `forward()`

---

## 8. Test Suite

33 new unit tests were added at `tests/unit/test_behavior_model.py`.

### Test classes

| Class | Tests | Coverage |
|---|---|---|
| `TestBehaviorModelConfig` | 4 | Default values, custom values, JSON save/load round-trip, valid JSON output |
| `TestConstruction` | 8 | Default config, explicit config, LSTM and proj attributes, proj dimensions, `nn.Module`, single-layer guard |
| `TestForwardUnidirectional` | 5 | Output shape, dtype, batch=1, variable seq_len, single layer |
| `TestForwardBidirectional` | 2 | Output projected to `hidden_dim`, dtype |
| `TestForwardValidation` | 3 | Wrong vec_dim, 2-D input, 4-D input |
| `TestDeterminism` | 1 | Identical output for identical input in eval mode |
| `TestPersistence` | 6 | File created, parent dirs, config restored, weights restored, missing file, bidirectional round-trip |
| `TestTorchAbsentGuard` | 3 | `forward`, `save`, `load` raise `RuntimeError` when torch mocked absent |
| `TestPipelineIntegration` | 1 | `LogDataset` → `DataLoader` → `SystemBehaviorModel` batch shape `[4, 32]` |

### Test suite results

```
330 passed, 22 deselected in 10.12s
```

- **330 tests passed** (297 pre-Phase 4 + 33 new Phase 4 tests)
- **22 deselected** (slow/model-dependent tests, unchanged)
- **0 failures, 0 errors**

---

## 9. Risks and Limitations

| Risk | Severity | Mitigation |
|---|---|---|
| LSTM does not handle variable-length sequences within a batch (no `pack_padded_sequence`) | Low | All windows in `LogDataset` have fixed length `window_size`; padding is not needed. If streaming inference requires variable lengths, `pack_padded_sequence` can be added in Phase 7. |
| Hidden state initialisation is zero (no stateful streaming) | Low | Correct for batch training. Stateful streaming (carry hidden state across windows) is a Phase 7 concern. |
| `bidirectional=True` doubles parameter count and adds projection overhead | Low | Default is `False`; BiLSTM is available as an experimental option but should not be promoted to default without evaluation. |
| Forward pass does not use LSTM output sequence, only `h_n` | Low | The final hidden state is the standard architectural choice for producing a fixed context vector from a sequence. The full output sequence is used in more complex architectures (attention), which is deferred. |
| No gradient clipping | Medium | Should be added in the Phase 4 / 7 training loop to prevent exploding gradients in deep LSTMs. Not implemented here since no training loop exists yet. |

---

## 10. Infrastructure Safety

The following was verified after Phase 4:

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
| `models/baseline.pkl` | Unchanged |
| `models/transformer.pt` | Unchanged |
| `Dockerfile`, `docker-compose.yml` | Unchanged |
| `.github/workflows/ci.yml` | Unchanged |
| `requirements.txt` | Unchanged (torch already present) |
| Existing tests (297) | All passing |

**No existing module was modified.** `SystemBehaviorModel` is not imported by any existing module and has no effect on the production runtime path until Phase 7.

---

## 11. Phase Boundary

Phase 4 is complete. The following are deferred to later phases:

| Deferred item | Phase |
|---|---|
| `AnomalyDetector` (Denoising Autoencoder) | Phase 5 |
| `SeverityClassifier` (MLP severity predictor) | Phase 6 |
| `ProactiveMonitorEngine` (end-to-end orchestrator) | Phase 7 |
| Training loop for `SystemBehaviorModel` | Phase 7 |
| Stateful hidden-state streaming for real-time inference | Phase 7 |
| Wiring `SystemBehaviorModel` into the live `/ingest` pipeline | Phase 7 |

Phase 4 is complete. The repository is ready for Phase 5 (Anomaly Detection Engine — `AnomalyDetector` Denoising Autoencoder implementation).
