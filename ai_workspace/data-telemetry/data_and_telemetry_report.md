# Data Lineage & Runtime Telemetry Report

**Project:** predictive-log-anomaly-engine
**Report date:** 2026-03-05
**Author:** automated audit (Claude Code)
**Scope:** All data transformations and measured telemetry from raw ingestion through live API

> **Methodology:** Every number in this report is extracted from existing logs, stage reports,
> or artifact files. Numbers that could only be inferred from file sizes or timestamps are
> labelled **(inferred)**. Numbers that were not logged at all are labelled **MISSING**.

---

## 1. Executive Story (slide-ready)

The predictive-log-anomaly-engine began with **~28.5 GB of raw log files** from two public
datasets — BGL (supercomputer syslog) and HDFS (Hadoop distributed-file-system audit logs).
These were merged into a single 15.9-million-row CSV that forms the canonical dataset for all
downstream work.

From there, a **six-stage offline pipeline** transformed the raw text into ML-ready features:

1. **Template Mining** — regex rules collapsed free-form log messages to 7,833 reusable
   templates in under 10 seconds on a 1M-row demo sample.
2. **Sequence Building** — each log session was summarised as a 407-dimensional feature vector
   (token frequencies + bigrams) across 495,405 sessions in 70 seconds, peaking at 1.1 GB RAM.
3. **Unsupervised Model** — an IsolationForest trained on the full 495K sessions in under 1
   second (fit only), achieving F1 = 0.96 on BGL and a weak F1 = 0.05 on HDFS.
4. **Supervised HDFS Model** — a Logistic Regression (L2) beat HistGradientBoosting on the
   imbalanced HDFS subset (PR-AUC 0.23 vs 0.18), trained in 12 seconds.
5. **Runtime Calibration** — thresholds were set to target a 0.5 % alert rate on a live stream.
6. **Live Inference** — the ensemble processes 368 events/second at ~27 ms average window
   latency, fully CPU-based (no GPU).

The service is wrapped in a **FastAPI + Prometheus + Grafana** observability stack, containerised
with Docker Compose, and validated by a 233-test CI suite (211 fast / 22 slow).

---

## 2. Dataset Origins

| Source | Format | Raw Size | Rows (est.) | Label |
|--------|--------|----------|-------------|-------|
| BGL.log | Plain text | 709 MB | ~4.75M | 0 / 1 per line |
| HDFS_1/HDFS.log | Plain text | 1.5 GB | ~11.2M | session-level |
| HDFS_2/ (31 files) | Plain text | ~26.3 GB | — | session-level |
| **Merged output** | CSV | **2.6 GB** | **15,923,592** | 0/1 per row |

**Source:** `data/raw/` directory listing; `ai_workspace/logs/stage_01_data_full.log`

### Label Distribution in Merged Dataset

| Dataset | Label 0 (normal) | Label 1 (anomaly) | Anomaly % |
|---------|-------------------|-------------------|-----------|
| BGL | 348,460 | 4,399,503 | 92.7 % |
| HDFS | 10,887,379 | 288,250 | 2.6 % |
| **Total** | **11,235,839** | **4,687,753** | **29.4 %** |

**Source:** `ai_workspace/logs/stage_01_data_full.log` — label distribution table

---

## 3. Data Lineage: Stage-by-Stage Transformation

```
data/raw/                       [~28.5 GB — plain text logs]
   BGL.log (709 MB)
   HDFS_1/HDFS.log (1.5 GB)
   HDFS_2/*.log (~26.3 GB)
        |
        | merge + label → events_unified.csv (Stage 00)
        v
data/processed/events_unified.csv       [2.6 GB | 15,923,592 rows | 5 cols]
        |
        | stratified sample 1M rows (Stage 02-Sampling)
        v
data/processed/events_sample_1m.csv     [167 MB | 1,000,000 rows]
        |
        | 9-step regex template mining (Stage 03 / Stage 22)
        v
data/intermediate/events_with_templates.csv  [267 MB | 1,000,000 rows | 7 cols]
data/intermediate/templates.csv              [1.5 MB | 7,833 templates]
artifacts/templates.json                     [1.5 MB | 7,833 entries]
artifacts/vocab.json                         [1.5 MB | 7,835 entries]
        |
        | group by session_id; compute 407 features (Stage 06 / Stage 23 V2)
        v
data/intermediate/session_sequences_v2.csv   [22 MB | 495,405 sessions | 6 cols]
data/intermediate/session_features_v2.csv    [589 MB | 495,405 sessions | 407 cols]
        |                           |
        | IsolationForest           | Filter HDFS only (404,179 sessions)
        | (Stage 08 / Stage 24 V2)  | LogReg-L2 (Stage 12 / Stage 26 V2)
        v                           v
data/models/isolation_forest_v2.pkl     data/models/hdfs_supervised_best_v2.pkl
  [1.8 MB | n_estimators=300]            [13.6 KB | LogisticRegression L2]
data/intermediate/session_scores_v2.csv  data/intermediate/hdfs_supervised_scores_v2.csv
  [22 MB | 495,405 rows | 5 cols]         [17 MB | 404,179 rows | 5 cols]
        |
        | F1/ROC/PR evaluation (Stage 10 / Stage 25 V2)
        v
ai_workspace/reports/stage_25_evaluation_report_v2.md + 5 plots
        |
        | tokenize full 15.9M events → parquet (Stage 04)
        v
data/processed/events_tokenized.parquet  [17 MB | 1M demo rows | 6 cols]
data/processed/sequences_train.parquet   [35 KB]
data/processed/sequences_val.parquet     [7 KB]
data/processed/sequences_test.parquet    [7 KB]
        |
        | percentile threshold calibration (Stage 13 / Stage 31)
        v
artifacts/threshold_runtime.json         [3 thresholds: baseline / transformer / ensemble]
        |
        | live streaming inference (Stage 14 / Stage 05 Demo)
        v
reports/runtime_demo_results.csv         [288 KB | 1,991 windows]
reports/runtime_demo_evidence.jsonl      [3.4 MB | 1,991 events]
        |
        | FastAPI service + Prometheus + Grafana (Stage 15-16)
        v
POST /ingest → InferenceEngine → AlertManager → GET /alerts
GET /metrics (Prometheus scrape every 15s)
GET / (demo UI: Ingest / Alerts / RAG tabs)
```

---

## 4. Per-Stage Timing & Memory Summary

| Stage | Script / Component | Elapsed | Peak RAM | Input Size | Output Size | Evidence |
|-------|--------------------|---------|----------|------------|-------------|----------|
| S01 Data Load | stage_01_data | 51.6 s | 6,652 MB | 2.6 GB | 2.6 GB (same) | stage_01_data_full.log |
| S03 Template Mining | stage_22 | 9.2 s | 470 MB | 167 MB | 268 MB | stage_22_template_mining.log |
| S06 Sequence Build V2 | stage_23_v2 | 69.6 s | 1,138 MB | 267 MB | 611 MB | stage_23_sequence_v2.log |
| S07 Baseline Model V1 | stage_24 | 24.1 s | 1,407 MB | 300 MB | 22 MB | stage_24_model_report.md |
| S08 Baseline Model V2 | stage_24_v2 | 26.9 s | 2,529 MB | 589 MB | 23 MB | stage_24_baseline_model_v2.log |
| S10 Evaluation V2 | stage_25_v2 | 1.6 s | MISSING | 22 MB | ~0 (plots) | stage_25_evaluation_v2.log |
| S11 HDFS Supervised V1 | stage_26_v1 | 21.3 s | 4,344 MB | 589 MB | 17 MB | stage_26_hdfs_supervised_report_v1.md |
| S12 HDFS Supervised V2 | stage_26_v2 | 51.4 s | 3,418 MB | 589 MB | 17 MB | stage_26_hdfs_supervised_v2.log |
| S13 Calibration | stage_31 | 6.04 s | MISSING | 17 MB | <1 MB | stage_31_runtime_calibration_report.md |
| S14 Runtime Demo | stage_05_demo | 54.4 s | 461 MB | 17 MB | 3.7 MB | stage_05_runtime_demo.log |

**CPU utilization was not profiled** in any stage script. All runs were on a single Windows 11 host (no GPU).

---

## 5. Model Performance Summary

| Model | Dataset | ROC-AUC | PR-AUC | F1 | Precision | Recall | Evidence |
|-------|---------|---------|--------|-----|-----------|--------|----------|
| IsolationForest V2 (overall) | BGL + HDFS | 0.563 | 0.213 | 0.385 | 0.254 | 0.795 | stage_24_baseline_model_v2.log |
| IsolationForest V2 | BGL only | 0.619 | 0.960 | 0.965 | 0.932 | 1.000 | stage_24_baseline_model_v2.log |
| IsolationForest V2 | HDFS only | 0.492 | 0.024 | 0.047 | — | — | stage_25_evaluation_v2.log |
| LogReg-L2 (HDFS supervised) | HDFS test | 0.660 | 0.233 | 0.252 | 0.426 | 0.179 | stage_26_hdfs_supervised_v2.log |
| HistGradientBoosting (HDFS) | HDFS val | — | 0.185 | — | — | — | stage_26_hdfs_supervised_v2.log |

---

## 6. Runtime Inference Telemetry

| Metric | Baseline Mode | Ensemble Mode | Unit | Evidence |
|--------|--------------|---------------|------|----------|
| Events processed | 20,000 | 20,000 | events | stage_05_runtime_demo.log |
| Windows emitted | 1,991 | 1,991 | windows | stage_05_runtime_demo.log |
| Elapsed time | — | 54.39 | seconds | stage_05_runtime_demo.log |
| Throughput | 743.7 | 367.7 | events/sec | stage_05_runtime_inference_report.md |
| Avg window latency | 13.1 | 27.0 | ms | stage_05_runtime_inference_report.md |
| P95 window latency | 15.6 | 31.3 | ms | stage_05_runtime_inference_report.md |
| Peak RSS | 428 MB | 461 MB | MB | stage_05_runtime_inference_report.md |
| Artifact load time | 0.05 s | 0.18 s | seconds | stage_05_runtime_inference_report.md |
| GPU utilization | N/A | N/A | — | No GPU; CPU-only |

### Runtime Calibration (threshold_runtime.json)

| Model | Threshold | Score Min | Score Max | Alert Rate Target |
|-------|-----------|-----------|-----------|-------------------|
| Baseline (IsolationForest) | 0.540392 | 0.464332 | 0.540411 | 0.5 % |
| Transformer | 9.195779 | 8.757017 | 9.232652 | 0.5 % |
| Ensemble | 135.831158 | 129.355448 | 136.368338 | 0.5 % |

**Source:** `artifacts/threshold_runtime.json`

---

## 7. Observability Infrastructure

| Component | Value | Source |
|-----------|-------|--------|
| API port | 8000 | docker-compose.yml |
| Prometheus port | 9090 | docker-compose.yml |
| Grafana port | 3000 | docker-compose.yml |
| Scrape interval | 15 s | prometheus/prometheus.yml |
| Metrics endpoint | GET /metrics | src/observability/metrics.py |
| Metrics exposed | 6 (see below) | src/observability/metrics.py |
| Grafana dashboards | 1 (stage08_api_observability.json, 5 panels) | grafana/dashboards/ |
| Grafana version | 10.4.2 | docker-compose.yml |
| Prometheus version | 2.51.0 | docker-compose.yml |

**Prometheus metrics defined:**

| Metric name | Type | Description |
|-------------|------|-------------|
| `ingest_events_total` | Counter | Total log events received via POST /ingest |
| `ingest_windows_total` | Counter | Total inference windows emitted |
| `alerts_total` | Counter | Total alerts raised (by severity) |
| `ingest_errors_total` | Counter | Total ingest validation errors |
| `ingest_latency_seconds` | Histogram | End-to-end POST /ingest latency |
| `scoring_latency_seconds` | Histogram | Inference engine scoring latency per window |

**Note:** No Prometheus snapshot or exported metric values exist in the repo. The p50/p95 API
latencies are **MISSING** from persisted artifacts (metrics are live-only).

---

## 8. CI/CD Summary

| Metric | Value | Source |
|--------|-------|--------|
| Total tests collected | 233 | STAGE_08_CLOSEOUT.md |
| Fast suite (-m "not slow") | 211 | STAGE_08_CLOSEOUT.md |
| Slow tests deselected in CI | 22 | STAGE_08_CLOSEOUT.md |
| Pipeline smoke tests (always fast) | 18 | tests/test_pipeline_smoke.py |
| Integration tests | 11 | tests/integration/test_smoke_api.py |
| CI jobs | 3 (tests / security / docker) | .github/workflows/ci.yml |
| CI test elapsed | MISSING | Not exported to repo artifacts |
| Security scan | pip-audit + trivy | .github/workflows/ci.yml |

---

## 9. Intermediate & Processed File Inventory

### data/intermediate/

| File | Size | Rows | Cols | Created |
|------|------|------|------|---------|
| events_with_templates.csv | 267 MB | 1,000,000 | 7 | 2026-03-03 09:59 |
| session_sequences.csv | 22 MB | 495,405 | 6 | 2026-03-03 12:28 |
| session_sequences_v2.csv | 22 MB | 495,405 | 6 | 2026-03-03 12:50 |
| session_features.csv | 300 MB | 495,405 | 204 | 2026-03-03 12:28 |
| session_features_v2.csv | 589 MB | 495,405 | 407 | 2026-03-03 12:51 |
| session_scores.csv | 21 MB | 495,405 | 5 | 2026-03-03 12:35 |
| session_scores_v2.csv | 22 MB | 495,405 | 5 | 2026-03-03 12:55 |
| hdfs_supervised_scores_v1.csv | 17 MB | 404,179 | 5 | 2026-03-03 13:05 |
| hdfs_supervised_scores_v2.csv | 17 MB | 404,179 | 5 | 2026-03-03 14:26 |
| templates.csv | 1.5 MB | 7,833 | 4 | 2026-03-03 09:59 |

### data/models/

| File | Size | Type | Created |
|------|------|------|---------|
| isolation_forest.pkl | 1.1 MB | IsolationForest (200 estimators) | 2026-03-03 12:35 |
| isolation_forest_v2.pkl | 1.8 MB | IsolationForest (300 estimators) | 2026-03-03 12:55 |
| hdfs_logreg_v1.pkl | 14 KB | LogisticRegression + StandardScaler | 2026-03-03 13:05 |
| hdfs_supervised_best_v2.pkl | 13.6 KB | LogisticRegression L2 (best) | 2026-03-03 14:26 |

### data/processed/ (key files)

| File | Size | Format | Notes |
|------|------|--------|-------|
| events_unified.csv | 2.6 GB | CSV | Canonical 15.9M-row dataset |
| events_sample_1m.csv | 167 MB | CSV | Stratified 1M-row demo sample |
| events_tokenized.parquet | 17 MB | Parquet | Token IDs for runtime inference |
| sequences_train.parquet | 35 KB | Parquet | Demo-mode train split |
| sequences_val.parquet | 7 KB | Parquet | Demo-mode val split |
| sequences_test.parquet | 7 KB | Parquet | Demo-mode test split |

### artifacts/

| File | Size | Contents |
|------|------|---------|
| templates.json | 1.5 MB | 7,833 template entries |
| vocab.json | 1.5 MB | 7,835 vocab entries |
| threshold.json | <1 KB | Thresholds for 3 model modes |
| threshold_runtime.json | <1 KB | Calibrated thresholds + score stats |

---

## 10. Known Gaps / How to Measure Next Time

The following metrics are **MISSING** from current artifacts. Each fix is minimal and surgical.

| Gap | Impact | Fix (1-2 lines of code) |
|-----|--------|--------------------------|
| **CPU % per stage** | Can't size instance type | Add `psutil.cpu_percent(interval=1)` poll before/after heavy loops; print to log |
| **Stage start/end wall-clock timestamps** | Timeline CSV relies on log header only | Wrap each stage script's `main()` with `time.strftime` print at entry and exit |
| **API latency p50/p95 (persisted)** | Can't show SLA compliance without a running instance | Add a `/metrics/snapshot` endpoint or scrape Prometheus and write JSON to `artifacts/metrics_snapshot_<date>.json` after each CI docker smoke |
| **alerts_total in CI** | Unknown production alert rate baseline | CI smoke script already POSTs 10 events; add `curl /metrics | grep alerts_total` and append to CI log |
| **Peak RSS for Evaluation stage (S10)** | Minor gap | The evaluation script doesn't call `resource.getrusage` or `psutil`; add 2-line memory hook like all other scripts |
| **HDFS V1 supervised log file** | V1 timing comes from report MD, not raw log | Save log file at `ai_workspace/logs/stage_26_hdfs_supervised_v1.log` the same way V2 does |
| **CI elapsed time per job** | Can't track CI regression | `github.run_id` is already in workflow; add `echo "elapsed=$SECONDS"` at end of each job step |
| **File sizes logged per stage** | Timeline CSV currently uses directory listing (inferred) | Add `os.path.getsize(output_path)` print after each file write in stage scripts |
| **GPU utilization** | Future transformer training may use GPU | Instrument with `pynvml` or `nvidia-smi dmon`; log N/A until GPU is introduced |
| **Prometheus snapshot export** | API latency p50/p95 not persisted | Run `curl localhost:9090/api/v1/query?query=ingest_latency_seconds` at end of docker smoke and save to `artifacts/` |

---

## 11. Evidence Sources

All numbers in this report were extracted from the following files:

| File | What was extracted |
|------|--------------------|
| `ai_workspace/logs/stage_01_data_full.log` | Data load elapsed, peak RSS, row count, label distribution |
| `ai_workspace/logs/stage_22_template_mining.log` | Template mining elapsed, peak RSS, memory start, template count |
| `ai_workspace/logs/stage_23_sequence_v2.log` | Sequence build elapsed, peak RSS, session count, bigram count, memory checkpoints |
| `ai_workspace/logs/stage_24_baseline_model_v2.log` | Baseline model elapsed, peak RSS, fit time, score range/mean, F1/P/R, threshold |
| `ai_workspace/logs/stage_25_evaluation_v2.log` | Evaluation elapsed, ROC/PR AUC by dataset and mode |
| `ai_workspace/logs/stage_26_hdfs_supervised_v2.log` | HDFS supervised elapsed, peak RSS, per-model fit times, PR-AUC, best threshold |
| `ai_workspace/logs/stage_05_runtime_demo.log` | Streaming demo elapsed, events_per_sec, windows_emitted |
| `ai_workspace/reports/system/stage_05_runtime_inference_report.md` | Avg/P95 latency, peak RSS, artifact load time, baseline vs ensemble comparison |
| `ai_workspace/reports/system/stage_31_runtime_calibration_report.md` | Calibration elapsed, window count, threshold values |
| `ai_workspace/reports/system/stage_24_model_report.md` | V1 baseline elapsed + peak RSS |
| `ai_workspace/reports/system/stage_26_hdfs_supervised_report_v1.md` | V1 HDFS supervised elapsed + peak RSS |
| `ai_workspace/reports/system/STAGE_08_CLOSEOUT.md` | CI test counts, docker jobs, ingest->alert fix |
| `artifacts/threshold_runtime.json` | Calibrated thresholds, score min/max per model |
| `prometheus/prometheus.yml` | Scrape interval, job name, metrics path |
| `docker-compose.yml` | Port mappings, service names, demo env vars, image versions |
| `src/observability/metrics.py` | Metric names and types |
| `data/raw/` directory listing | Raw file names and sizes |
| `data/intermediate/` directory listing | Intermediate file sizes and modification timestamps |
| `data/models/` directory listing | Model file sizes and modification timestamps |
| `data/processed/` directory listing | Processed file sizes and modification timestamps |
| `ai_workspace/reports/system/stage_27_stages_0_4_completion_report.md` | Stage 00 context and full dataset row counts |
| `.github/workflows/ci.yml` | CI job structure, test commands, security scan |
