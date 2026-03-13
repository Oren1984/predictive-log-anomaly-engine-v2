# Operational Runbook

**Project:** Predictive Log Anomaly Engine
**Date:** 2026-03-04
**Stage:** 09 - Repository Documentation Finalization

---

## Overview

This runbook provides step-by-step instructions for running the Predictive Log Anomaly Engine
from scratch. Follow the sections in order for a complete fresh setup, or jump to a specific
section for targeted operations.

---

## 1. Environment Preparation

### 1.1 Clone the Repository

```bash
git clone <repository-url>
cd predictive-log-anomaly-engine
```

### 1.2 Python Environment

```bash
# Verify Python version (must be 3.11+)
python --version

# Create a virtual environment (recommended)
python -m venv .venv

# Activate on Linux/macOS
source .venv/bin/activate

# Activate on Windows (bash)
source .venv/Scripts/activate
```

### 1.3 Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development + testing dependencies (add for test runs)
pip install -r requirements-dev.txt
```

### 1.4 Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit as needed
# Minimum changes for local development:
# - Set API_KEY to a non-default value for security
# - For demo mode: DEMO_MODE=true, DISABLE_AUTH=true
```

Key variables to review:

```
DEMO_MODE=false          # Set true if no model files available
DISABLE_AUTH=false       # Set true for local dev (no API key needed)
MODEL_MODE=ensemble      # baseline | transformer | ensemble
WINDOW_SIZE=50           # Events per inference window
STRIDE=10                # Window step after first window
ALERT_COOLDOWN_SECONDS=60.0
```

---

## 2. Pipeline Execution Order

### 2.1 Complete Pipeline (Offline + Runtime)

Run stages in this order. Each stage depends on outputs from previous stages.

```
Stage 20 (prep) → Stage 22 → Stage 23 → Stage 24 → Stage 25 → Stage 26 → Stage 7 (API)
```

### 2.2 Prerequisites Check

Before running offline stages, verify input data exists:

```bash
# Check for events_unified.csv (required for Stage 22)
ls -lh data/processed/events_unified.csv
# Expected: ~15.9M rows CSV, ~2-3 GB

# Check intermediate files (required for each subsequent stage)
ls -lh data/intermediate/
```

---

## 3. Stage Execution

### Stage 20 — Data Preparation (if needed)

If `data/processed/events_unified.csv` does not exist:

```bash
# Download raw HDFS and BGL datasets first (manual step)
# Place in data/raw/HDFS/ and data/raw/BGL/

# Prepare unified events file
python scripts/20_prepare_events.py
```

Expected output: `data/processed/events_unified.csv` (~15.9M rows)

---

### Stage 22 — Template Mining

**Script:** `ai_workspace/stage_22_template_mining/run_template_mining.py`
**Input:** `data/processed/events_unified.csv` (or sampled subset)
**Runtime:** ~9 seconds for 1M rows; longer for full dataset
**Peak memory:** ~470 MB

```bash
python ai_workspace/stage_22_template_mining/run_template_mining.py
```

**Outputs:**

| File | Location | Description |
|------|----------|-------------|
| Events with templates | `data/intermediate/events_with_templates.csv` | 1M rows + template_id + template_text |
| Template dictionary | `data/intermediate/templates.csv` | 7,833 templates with counts and anomaly rates |

**Log:** `ai_workspace/logs/stage_22_template_mining.log`
**Report:** `ai_workspace/reports/stage_22_template_report.md`

**Verification:**
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/intermediate/templates.csv')
print(f'Templates: {len(df)} (expected: ~7833)')
"
```

---

### Stage 23 — Sequence Building

**Script:** `ai_workspace/stage_23_sequence_builder/run_sequence_builder_v2.py`
**Input:** `data/intermediate/events_with_templates.csv`
**Runtime:** ~70 seconds
**Peak memory:** ~1138 MB

```bash
python ai_workspace/stage_23_sequence_builder/run_sequence_builder_v2.py
```

**Outputs:**

| File | Location | Description |
|------|----------|-------------|
| Session sequences | `data/intermediate/session_sequences_v2.csv` | 495,405 rows x 6 cols |
| Session features | `data/intermediate/session_features_v2.csv` | 495,405 rows x 407 cols |

**Log:** `ai_workspace/logs/stage_23_sequence_v2.log`

**Verification:**
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/intermediate/session_features_v2.csv', nrows=5)
print(f'Columns: {len(df.columns)} (expected: 407)')
"
```

---

### Stage 24 — Baseline Model Training

**Script:** `ai_workspace/stage_24_baseline_model/run_baseline_model_v2.py`
**Input:** `data/intermediate/session_features_v2.csv`
**Runtime:** ~27 seconds
**Peak memory:** ~2528 MB

```bash
python ai_workspace/stage_24_baseline_model/run_baseline_model_v2.py
```

**Outputs:**

| File | Location | Description |
|------|----------|-------------|
| Model pickle | `data/models/isolation_forest_v2.pkl` | IsolationForest, n_estimators=300 (~1.8 MB) |
| Session scores | `data/intermediate/session_scores_v2.csv` | 495,405 rows with predictions |

**Log:** `ai_workspace/logs/stage_24_baseline_model_v2.log`
**Report:** `ai_workspace/reports/stage_24_model_report_v2.md`

**Expected metrics:**
- Overall F1=0.385, P=0.254, R=0.795
- BGL F1=0.965 (strong)
- HDFS F1=0.047 (weak — motivates Stage 26)

---

### Stage 25 — Evaluation

**Script:** `ai_workspace/stage_25_evaluation/run_evaluation_v2.py`
**Input:** `data/intermediate/session_scores_v2.csv`
**Runtime:** ~2 seconds

```bash
python ai_workspace/stage_25_evaluation/run_evaluation_v2.py
```

**Outputs:** ROC curve, PR curve, score histogram, confusion matrix plots (PNG files)
**Report:** `ai_workspace/reports/stage_25_evaluation_report_v2.md`

---

### Stage 26 — Supervised HDFS Model

**Script:** `ai_workspace/stage_26_hdfs_supervised/run_hdfs_supervised_v2.py`
**Input:** `data/intermediate/session_features_v2.csv`
**Runtime:** ~52 seconds
**Peak memory:** ~3417 MB

```bash
python ai_workspace/stage_26_hdfs_supervised/run_hdfs_supervised_v2.py
```

**Outputs:**

| File | Location | Description |
|------|----------|-------------|
| Model pickle | `data/models/hdfs_supervised_best_v2.pkl` | LogReg-L2 (~13.6 KB) |
| Scores | `data/intermediate/hdfs_supervised_scores_v2.csv` | 404,179 rows |

**Expected metrics:**
- PR-AUC=0.2334, F1=0.252, P=0.426, R=0.179 (test split)

---

## 4. Running the API

### 4.1 Option A: Docker Compose (Recommended)

```bash
# Start all services (API + Prometheus + Grafana)
docker compose up -d --build

# Wait for API ready
until curl -sf http://localhost:8000/health > /dev/null; do
  echo "Waiting for API..."; sleep 2
done
echo "API is ready"

# View logs
docker compose logs -f api

# Stop all services
docker compose down -v
```

**Service URLs:**
- API: http://localhost:8000
- Demo UI: http://localhost:8000/
- API docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

### 4.2 Option B: Local Python (No Docker)

```bash
# Set demo mode for development (no model files needed)
export DEMO_MODE=true
export DISABLE_AUTH=true
export WINDOW_SIZE=5
export STRIDE=1
export ALERT_COOLDOWN_SECONDS=0
export DEMO_WARMUP_ENABLED=true

# Start the API server
python -m uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

### 4.3 Option C: In-Process Demo (No Server)

```bash
# Fastest option: no server, no Docker, ~0.5 seconds
python scripts/demo_run.py
```

---

## 5. Verifying the System

### 5.1 API Smoke Tests

```bash
# Health check
curl -s http://localhost:8000/health | python -m json.tool

# Ingest a test event
curl -s -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"service":"test","session_id":"s1","token_id":1,"label":0}' \
  | python -m json.tool

# Check alerts
curl -s http://localhost:8000/alerts | python -m json.tool

# Check metrics
curl -s http://localhost:8000/metrics | grep -E "^(ingest|alerts)" | head -10

# Demo UI
curl -s http://localhost:8000/ | grep -o '<title>.*</title>'
```

### 5.2 Run the Test Suite

```bash
# Fast suite (211 tests, ~12 seconds) — works without model files
pytest -m "not slow"

# With verbose output
pytest -m "not slow" -v

# Specific test file
pytest tests/test_pipeline_smoke.py -v

# Integration tests only (requires running API or TestClient)
pytest -m "integration" -v
```

---

## 6. Data File Locations

### 6.1 Input Data

| File | Path | Size | Notes |
|------|------|------|-------|
| Unified events | `data/processed/events_unified.csv` | ~2 GB | 15.9M rows |
| Raw HDFS logs | `data/raw/HDFS/` | ~1.5 GB | Source data |
| Raw BGL logs | `data/raw/BGL/` | ~700 MB | Source data |

### 6.2 Intermediate Data

| File | Path | Produced By |
|------|------|-------------|
| Events with templates | `data/intermediate/events_with_templates.csv` | Stage 22 |
| Template dictionary | `data/intermediate/templates.csv` | Stage 22 |
| Session sequences v2 | `data/intermediate/session_sequences_v2.csv` | Stage 23 |
| Session features v2 | `data/intermediate/session_features_v2.csv` | Stage 23 |
| Session scores v2 | `data/intermediate/session_scores_v2.csv` | Stage 24 |
| HDFS supervised scores | `data/intermediate/hdfs_supervised_scores_v2.csv` | Stage 26 |

### 6.3 Model Artifacts

| File | Path | Produced By | Required At Runtime |
|------|------|-------------|---------------------|
| IsolationForest v2 | `data/models/isolation_forest_v2.pkl` | Stage 24 | Yes (baseline mode) |
| HDFS LogReg v2 | `data/models/hdfs_supervised_best_v2.pkl` | Stage 26 | No (not yet in runtime path) |
| Runtime models | `models/` | Copied from data/models/ | Yes (API startup) |

**Note:** Copy models to the runtime directory before starting the API with real models:
```bash
cp data/models/isolation_forest_v2.pkl models/
```

### 6.4 Output Artifacts

| File | Path | Description |
|------|------|-------------|
| Alert outbox | `artifacts/n8n_outbox/*.json` | N8n webhook dry-run outputs |
| Stage logs | `ai_workspace/logs/stage_*.log` | Per-stage execution logs |
| Stage reports | `ai_workspace/reports/stage_*.md` | Per-stage metric reports |
| Evaluation plots | `ai_workspace/reports/` | PNG plots from Stage 25 |

---

## 7. Troubleshooting

### 7.1 API Will Not Start

**Symptom:** `docker compose up` fails or API container exits immediately.

**Check:**
```bash
docker compose logs api
```

**Common causes:**

| Error | Fix |
|-------|-----|
| `Port 8000 already in use` | `lsof -i :8000` then kill the process |
| `ModuleNotFoundError: src.api.app` | Ensure `PYTHONPATH=/app` is set; verify Dockerfile |
| `FileNotFoundError: templates/index.html` | Check `.dockerignore` — templates/ must not be excluded |
| `Permission denied on artifacts/` | `chmod 777 artifacts/` or check volume mount |

### 7.2 Health Check Returns "degraded" or "unhealthy"

**Check:**
```bash
curl -s http://localhost:8000/health | python -m json.tool
```

**Common causes:**

| Component Status | Meaning |
|-----------------|---------|
| `inference_engine: degraded` | Model files missing; set `DEMO_MODE=true` or copy models |
| `alert_buffer: unhealthy` | Alert manager initialization failed (rare) |

### 7.3 No Alerts Being Generated

**Symptom:** POST /ingest returns `"window_emitted": true` but `"alert": null`.

**Checks:**
1. `risk_score` in the response — is it above the threshold?
2. `ALERT_COOLDOWN_SECONDS` — if set high, alerts will be suppressed for that stream
3. `DEMO_MODE` — must be `true` and `DEMO_SCORE` must exceed threshold

```bash
# Reset cooldown: set to 0
export ALERT_COOLDOWN_SECONDS=0
# Or in docker-compose.yml: ALERT_COOLDOWN_SECONDS: "0"
```

### 7.4 Window Never Emitted

**Symptom:** All /ingest responses show `"window_emitted": false`.

**Check:** `WINDOW_SIZE` setting vs. number of events ingested.

```bash
# Default WINDOW_SIZE=50 — need 50 events from the same stream_key
# For demo: set WINDOW_SIZE=5
export WINDOW_SIZE=5
export STRIDE=1
```

**Also check:** All events use the same `service` AND `session_id`. The `stream_key` is
`f"{service}:{session_id}"`. Mixed services create separate buffers.

### 7.5 Stage 22 / 23 / 24 Out of Memory

**Symptom:** Python process killed during offline pipeline stages.

**Minimum memory requirements:**

| Stage | Peak RAM |
|-------|---------|
| Stage 22 | 470 MB |
| Stage 23 | 1138 MB |
| Stage 24 | 2528 MB |
| Stage 26 | 4344 MB |

**Mitigations:**
- Close other applications before running stages 24 and 26
- Stage 26: The script includes `del df_full` after HDFS filter — do not remove this
- If Stage 24 OOMs, reduce the sample size in Stage 23 (fewer sessions)

### 7.6 pytest Test Failures

**Symptom:** Unexpected test failures.

```bash
# Run with verbose output to see which tests fail
pytest -m "not slow" -v --tb=short

# Check if slow tests are being included accidentally
pytest --co -q | grep slow

# Run a single failing test with full output
pytest tests/test_pipeline_smoke.py::test_ingest_event -s -v
```

**Common causes:**

| Failure | Fix |
|---------|-----|
| `ImportError` | Ensure `pip install -r requirements.txt -r requirements-dev.txt` |
| `FileNotFoundError: sequences_train.parquet` | These are `@pytest.mark.slow` tests; use `-m "not slow"` |
| `AssertionError` in integration tests | API may be starting slowly; TestClient should be instant |

### 7.7 Grafana Shows No Data

**Symptom:** Grafana dashboard panels show "No data".

**Checks:**
1. Is Prometheus scraping successfully? Check http://localhost:9090/targets
2. Has any traffic hit the API? Send some events first
3. Check time range in Grafana — set to "Last 5 minutes"
4. Verify datasource: Dashboards → Configuration → Data Sources → Prometheus → Test

### 7.8 Docker Build Fails

**Symptom:** `docker build` exits with error.

```bash
# Build with verbose output
docker build --no-cache --progress=plain . 2>&1 | tail -30
```

**Common causes:**

| Error | Fix |
|-------|-----|
| `pip install` fails | Check requirements.txt for version conflicts; try without version pins |
| `COPY models/` fails | The Dockerfile uses `RUN mkdir -p models artifacts` — ensure this is present |
| `curl: not found` | HEALTHCHECK requires curl; ensure `apt-get install curl` in Dockerfile |

---

## 8. CI/CD Reference

### 8.1 GitHub Actions Workflow

File: `.github/workflows/ci.yml`

Three jobs run on every push and pull request:

| Job | Trigger | Steps |
|-----|---------|-------|
| `tests` | Always | Install deps → flake8 lint → pytest -m "not slow" |
| `security` | Always | pip-audit → trivy filesystem scan |
| `docker` | Always | mkdir models artifacts → docker build → compose up → smoke tests → compose down |

### 8.2 CI Smoke Test Steps

The docker job runs these checks in order:
1. `docker compose up -d --build`
2. Wait up to 90s for `GET /health` → 200
3. `GET /metrics` → 200
4. `POST /ingest` × 10 events
5. `GET /alerts` → count >= 1
6. `GET /` → 200 (demo UI)
7. `POST /query` → 200 (RAG stub)
8. `docker compose down -v`

### 8.3 Running CI Locally

```bash
# Replicate the full CI locally
chmod +x scripts/smoke_test.sh
./scripts/smoke_test.sh
```

---

## 9. Quick Reference Card

```
SETUP:
  pip install -r requirements.txt -r requirements-dev.txt
  cp .env.example .env

OFFLINE PIPELINE:
  python ai_workspace/stage_22_template_mining/run_template_mining.py
  python ai_workspace/stage_23_sequence_builder/run_sequence_builder_v2.py
  python ai_workspace/stage_24_baseline_model/run_baseline_model_v2.py
  python ai_workspace/stage_25_evaluation/run_evaluation_v2.py
  python ai_workspace/stage_26_hdfs_supervised/run_hdfs_supervised_v2.py

START API (Docker):
  docker compose up -d --build
  curl http://localhost:8000/health

START API (local demo):
  DEMO_MODE=true DISABLE_AUTH=true WINDOW_SIZE=5 STRIDE=1 ALERT_COOLDOWN_SECONDS=0 \
    python -m uvicorn src.api.app:create_app --factory --port 8000

QUICK DEMO (no server):
  python scripts/demo_run.py

TESTS (fast, no models):
  pytest -m "not slow"

STOP API (Docker):
  docker compose down -v

KEY URLS:
  API        http://localhost:8000
  Demo UI    http://localhost:8000/
  API Docs   http://localhost:8000/docs
  Metrics    http://localhost:8000/metrics
  Health     http://localhost:8000/health
  Prometheus http://localhost:9090
  Grafana    http://localhost:3000 (admin/admin)
```
