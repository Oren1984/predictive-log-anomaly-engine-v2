# Stage 31 — Runtime Calibration Report

_Generated: 2026-03-09T06:40:55.949109+00:00_

## Command Used

```powershell
python scripts/stage_05_runtime_calibrate.py --mode demo --model ensemble --n-events 2000 --target-alert-rate 0.005
```

## Run Parameters

| Parameter | Value |
|-----------|-------|
| mode | demo |
| key_by | service |
| window_size | 50 |
| stride | 10 |
| n_events | 2,000 |
| n_windows (per model) | 192 |
| target_alert_rate | 0.005 |
| total elapsed (s) | 6.18 |

## Calibration Method

**Chosen method: `percentile`**

Labels were absent or contained only one class in the calibration windows, so **percentile calibration** was used: `threshold = quantile(scores, 1 - 0.005)`, targeting 0.50% of windows flagged.

## Calibrated Thresholds

| Model | Threshold | Method | Achieved Alert Rate |
|-------|-----------|--------|---------------------|
| baseline     | 0.540392 | percentile   | 0.521% |
| transformer  | 9.195779 | percentile   | 0.521% |
| ensemble     | 135.831158 | percentile   | 0.521% |

## Score Statistics

| Model | min | p50 | p95 | p99 | max |
|-------|-----|-----|-----|-----|-----|
| baseline     | 0.4643 | 0.5069 | 0.5337 | 0.5387 | 0.5404 |
| transformer  | 8.7570 | 8.9984 | 9.1118 | 9.1579 | 9.2327 |
| ensemble     | 129.3554 | 132.9086 | 134.5908 | 135.2969 | 136.3683 |

## Notes

- These are **demo-calibrated thresholds**, not production calibration.
  Production calibration requires a representative held-out labeled dataset.
- Thresholds target `0.50%` of streaming windows flagged as anomalies.
- To use calibrated thresholds in the runtime demo, pass `--use-runtime-thresholds`:

```powershell
python scripts/stage_05_runtime_demo.py --mode demo --model ensemble --use-runtime-thresholds
```

## Output Files

| File | Description |
|------|-------------|
| `artifacts/threshold_runtime.json` | Calibrated thresholds and score statistics |
| `reports/runtime_calibration_scores.csv` | Per-window scores (all models) |
| `reports/stage_31_runtime_calibration_report.md` | This report |
| `ai_workspace/logs/stage_05_runtime_calibrate.log` | Full execution log |
