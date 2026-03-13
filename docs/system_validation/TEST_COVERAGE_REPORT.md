# TEST COVERAGE REPORT
## Phase 7.5 — General System Validation

**Execution Date:** 2026-03-09
**Python Version:** 3.13.9
**pytest Version:** 9.0.2
**Project:** predictive-log-anomaly-engine

---

## Commands Executed

```bash
# Full suite (all tests)
pytest -q --tb=short
# Result: 604 passed in 59.73s

# Fast suite (excludes slow and integration)
pytest -q --tb=short -m "not slow and not integration"
# Result: 449 passed, 78 deselected in 16.96s

# System tests only
pytest tests/system/ -v --tb=short
# Result: 77 passed in 49.13s
```

---

## Test Distribution by Component

| Component / Test File | Tests | Passed | Failed | Pass Rate |
|---|---:|---:|---:|---:|
| **Unit: Proactive Engine** | 65 | 65 | 0 | 100% |
| **Unit: Anomaly Detector** | 63 | 63 | 0 | 100% |
| **Unit: Severity Classifier** | 47 | 47 | 0 | 100% |
| **Unit: Log Preprocessor** | 44 | 44 | 0 | 100% |
| **Unit: Log Dataset** | 42 | 42 | 0 | 100% |
| **Unit: Behavior Model** | 33 | 33 | 0 | 100% |
| **Unit: Sequence Buffer** | 23 | 23 | 0 | 100% |
| **Unit: Inference Engine Smoke** | 18 | 18 | 0 | 100% |
| **Unit: Sequences** | 17 | 17 | 0 | 100% |
| **Unit: Tokenizer** | 16 | 16 | 0 | 100% |
| **Unit: Explain / Decode** | 15 | 15 | 0 | 100% |
| **Unit: Calibrator** | 11 | 11 | 0 | 100% |
| **Unit: Synth Generation** | 7 | 7 | 0 | 100% |
| **Unit: Runtime Calibration** | 7 | 7 | 0 | 100% |
| **Alert: Alert Policy** | 20 | 20 | 0 | 100% |
| **Alert: Dedup / Cooldown** | 12 | 12 | 0 | 100% |
| **Alert: N8n Outbox** | 13 | 13 | 0 | 100% |
| **API: Pipeline Smoke** | 18 | 18 | 0 | 100% |
| **API: Auth (Stage 7)** | 11 | 11 | 0 | 100% |
| **API: Ingest Integration (Stage 7)** | 14 | 14 | 0 | 100% |
| **API: Metrics (Stage 7)** | 15 | 15 | 0 | 100% |
| **Integration: API Smoke** | 16 | 16 | 0 | 100% |
| **System: End-to-End Pipeline** _(NEW)_ | 27 | 27 | 0 | 100% |
| **System: Streaming Simulation** _(NEW)_ | 16 | 16 | 0 | 100% |
| **System: Model Fallback** _(NEW)_ | 30 | 30 | 0 | 100% |
| **System: Performance Validation** _(NEW)_ | 4 | 4 | 0 | 100% |
| **TOTAL** | **604** | **604** | **0** | **100%** |

---

## Test Category Summary

| Category | Test Count | Status |
|---|---:|---|
| Unit tests (logic, algorithms, models) | 330 | PASS |
| Alert / outbox tests | 45 | PASS |
| API / integration tests (HTTP layer) | 74 | PASS |
| System-level tests (Phase 7.5, new) | 77 | PASS |
| **Grand Total** | **604** | **PASS** |

---

## Slow Tests (deselected in fast CI suite)

The following test classes are marked `@pytest.mark.slow` and excluded from
the default CI run (`-m "not slow"`). They depend on trained model artifacts.

| Test Class | File | Reason |
|---|---|---|
| TestNoResultBeforeWindowFull | test_inference_engine_smoke.py | Needs baseline.pkl |
| TestRiskResultFields | test_inference_engine_smoke.py | Needs baseline.pkl |
| TestEngineStride | test_inference_engine_smoke.py | Needs baseline.pkl |
| TestScoreBaseline | test_inference_engine_smoke.py | Needs baseline.pkl |
| TestTransformerSmoke | test_inference_engine_smoke.py | Needs transformer.pt |
| TestRiskResultSerialisation | test_inference_engine_smoke.py | Needs baseline.pkl |
| TestRuntimeCalibration | test_runtime_calibration.py | Model-artifact dependent |
| TestPerformanceThroughput | test_performance_validation.py | Long-running (10k events) |

> Note: All slow tests run and pass in extended mode (`pytest` without `-m` filter).
> Total with slow tests: **604 passed in 59.73s**.

---

## Overall Result

```
OVERALL: PASS
604 tests collected
604 passed
0 failed
0 errors
Execution time: 59.73 seconds (full suite)
```
