# Scripts

This directory contains the active pipeline scripts for the anomaly detection system.
Scripts follow the `stage_NN_name.py` naming convention, ordered by pipeline stage.

---

## Active Scripts

| Script | Stage | Purpose |
|--------|-------|---------|
| `stage_01_data.py` | 1 | Download/prepare raw HDFS + BGL datasets |
| `stage_01_synth_generate.py` | 1 | Generate synthetic log events for testing |
| `stage_01_synth_to_processed.py` | 1 | Convert synthetic events to processed CSV |
| `stage_01_synth_validate.py` | 1 | Validate synthetic data integrity |
| `stage_02_templates.py` | 2 | Mine log templates via 9-step regex pipeline |
| `stage_03_sequences.py` | 3 | Build session sequences and feature vectors |
| `stage_04_baseline.py` | 4 | Train IsolationForest baseline model |
| `stage_04_transformer.py` | 4 | Train LSTM transformer model |
| `stage_05_run.py` | 5 | Run real-time inference engine demo |
| `stage_06_demo_alerts.py` | 6 | Demo alert system with synthetic events |
| `stage_07_run_api.py` | 7 | **Start the FastAPI server** (primary entrypoint) |
| `demo_run.py` | — | Fast in-process demo (~0.5s, 75 events via TestClient) |
| `smoke_test.sh` | — | Idempotent local Docker smoke test |
| `00_check_env.ps1` | — | PowerShell: verify environment prerequisites |

---

## Quick Start

```bash
# Start the API (also available via main.py or docker-compose)
python scripts/stage_07_run_api.py

# Run in-process demo (no Docker needed)
python scripts/demo_run.py

# Full Docker smoke test
./scripts/smoke_test.sh
```

---

## Archive

Legacy and superseded scripts have been moved to `scripts/archive/`:

| Script | Reason Archived |
|--------|----------------|
| `10_download_data.py` – `90_run_api.py` | Older `NN_*.py` naming scheme; superseded by `stage_0N_*.py` equivalents |
| `run_0_4.py` | Legacy meta-runner; superseded by individual stage scripts |
| `stage_05_runtime_benchmark.py` | Development benchmarking; not part of production pipeline |
| `stage_05_runtime_calibrate.py` | Development calibration; now embedded in InferenceEngine |
| `stage_05_runtime_demo.py` | Superseded by `demo_run.py` (faster, in-process) |
| `validation/run_*_validation.py` | One-off dev validation tools |
