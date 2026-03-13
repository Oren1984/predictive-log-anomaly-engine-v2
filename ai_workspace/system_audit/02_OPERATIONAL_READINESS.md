# Operational Readiness

**Project:** Predictive Log Anomaly Engine
**Date:** 2026-03-04
**Stage:** 09 - Repository Documentation Finalization

---

## 1. Environment Requirements

### 1.1 Host Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.11 | 3.11 (matches Docker base) |
| RAM | 4 GB | 8 GB (pipeline stages peak at 3.4 GB) |
| Disk | 5 GB | 10 GB (raw datasets + intermediates + models) |
| OS | Linux, macOS, Windows 11 | Linux (production) |
| Docker | 24.x | Latest stable |
| Docker Compose | v2.x | Latest stable |
| curl | Any | Required for smoke tests |

### 1.2 Critical Environment Note
The project uses **Python `python` command** (not `python3`). On systems where both exist,
ensure the default `python` resolves to Python 3.11+.

```bash
python --version  # Must be 3.x
```

### 1.3 Console Encoding
Standard output encoding is `cp1255`. Avoid printing non-ASCII characters (em-dashes,
arrows, Unicode symbols) in scripts that write to the console.

---

## 2. Python Dependencies

### 2.1 Production Dependencies (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115.6 | REST API framework |
| uvicorn | >=0.41.0 | ASGI server |
| httpx | >=0.28.1 | Async HTTP client (n8n, tests) |
| prometheus-client | >=0.24.1 | Metrics export |
| numpy | >=2.4.0 | Numerical operations |
| pandas | >=3.0.0 | Data manipulation |
| scikit-learn | >=1.8.0 | IsolationForest, LogReg, preprocessing |
| torch | >=2.10.0 | Transformer model |
| pyarrow | >=23.0.1 | Parquet file I/O |
| psutil | >=7.2.2 | System metrics |

### 2.2 Development Dependencies (`requirements-dev.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0.0 | Test runner |
| pytest-cov | >=5.0.0 | Coverage reporting |
| ruff | >=0.6.0 | Linter/formatter |
| flake8 | >=7.0.0 | CI lint check |

### 2.3 Installation

```bash
# Production
pip install -r requirements.txt

# Development (includes production deps)
pip install -r requirements.txt -r requirements-dev.txt
```

---

## 3. Environment Variable Configuration

Copy `.env.example` to `.env` before running locally.

```bash
cp .env.example .env
```

### 3.1 Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `changeme` | X-API-Key for protected endpoints |
| `MODEL_MODE` | `ensemble` | Scoring mode: `baseline`, `transformer`, `ensemble` |

### 3.2 Key Operational Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_MODE` | `false` | Use synthetic fallback score (no model files needed) |
| `DEMO_SCORE` | `2.0` | Fallback anomaly score in demo mode |
| `WINDOW_SIZE` | `50` | Events per inference window |
| `STRIDE` | `10` | Window step after first full window |
| `ALERT_COOLDOWN_SECONDS` | `60.0` | Per-stream alert deduplication window |
| `ALERT_BUFFER_SIZE` | `200` | Recent alerts ring buffer size |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics endpoint |
| `DISABLE_AUTH` | `false` | Bypass API key check (demo/dev only) |
| `N8N_DRY_RUN` | `true` | Write alerts to outbox instead of posting |

### 3.3 Demo Mode Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_WARMUP_ENABLED` | `false` | Ingest synthetic events on startup |
| `DEMO_WARMUP_EVENTS` | `75` | Number of warmup events to ingest |
| `DEMO_WARMUP_INTERVAL_SECONDS` | `0` | Delay between warmup events (0=burst) |

---

## 4. Docker Usage

### 4.1 Starting the Full Stack

```bash
docker compose up -d --build
```

This starts three services:

| Service | Port | URL |
|---------|------|-----|
| anomaly-api | 8000 | http://localhost:8000 |
| prometheus | 9090 | http://localhost:9090 |
| grafana | 3000 | http://localhost:3000 (admin/admin) |

### 4.2 Service Health Check

```bash
# Wait for API readiness
curl -f http://localhost:8000/health

# Expected response
{"status":"healthy","uptime_seconds":12.3,"components":{...}}
```

### 4.3 Stopping the Stack

```bash
docker compose down -v
```

### 4.4 Viewing Logs

```bash
# All services
docker compose logs -f

# API only
docker compose logs -f api
```

### 4.5 Local Smoke Test Script

```bash
chmod +x scripts/smoke_test.sh
./scripts/smoke_test.sh
```

The smoke test: stops any existing stack, builds, waits for HTTP 200 on `/health`,
verifies `/metrics`, ingests 10 events, checks that `/alerts` returns at least 1 alert,
then tears down.

---

## 5. Execution Commands

### 5.1 Running Tests

```bash
# Fast CI suite (211 tests, ~12 seconds)
pytest -m "not slow"

# Full suite including slow model tests
pytest

# Integration tests only
pytest -m "integration"

# With coverage report
pytest -m "not slow" --cov=src --cov-report=term-missing
```

### 5.2 Running the API Locally (without Docker)

```bash
# Set environment variables first
export DEMO_MODE=true DISABLE_AUTH=true WINDOW_SIZE=5 STRIDE=1

# Start API server
python scripts/90_run_api.py
# or
python -m uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

### 5.3 Quick In-Process Demo

```bash
# No server needed, uses TestClient, ~0.5 seconds
python scripts/demo_run.py
```

### 5.4 Offline Pipeline Stages

```bash
# Run each stage in order
python ai_workspace/stage_22_template_mining/run_template_mining.py
python ai_workspace/stage_23_sequence_builder/run_sequence_builder_v2.py
python ai_workspace/stage_24_baseline_model/run_baseline_model_v2.py
python ai_workspace/stage_25_evaluation/run_evaluation_v2.py
python ai_workspace/stage_26_hdfs_supervised/run_hdfs_supervised_v2.py
```

---

## 6. Expected Outputs

### 6.1 API Health Response

```json
{
  "status": "healthy",
  "uptime_seconds": 45.2,
  "components": {
    "inference_engine": {"status": "healthy", "artifacts_loaded": true},
    "alert_manager": {"status": "healthy"},
    "alert_buffer": {"status": "healthy", "size": 12}
  }
}
```

### 6.2 Ingest Response (with window)

```json
{
  "window_emitted": true,
  "risk_result": {
    "stream_key": "web-server:session-1",
    "model": "ensemble",
    "risk_score": 2.0,
    "is_anomaly": true,
    "threshold": 1.0,
    "evidence_window": {"tokens": [1, 5, 3, 2, 7], "window_start_ts": 1740000000.0}
  },
  "alert": {
    "alert_id": "uuid-...",
    "severity": "critical",
    "service": "web-server",
    "score": 2.0
  }
}
```

### 6.3 Pipeline Stage Outputs

| Stage | Expected Output Files |
|-------|----------------------|
| Stage 22 | `data/intermediate/events_with_templates.csv` (1M rows), `data/intermediate/templates.csv` |
| Stage 23 | `data/intermediate/session_sequences_v2.csv`, `data/intermediate/session_features_v2.csv` |
| Stage 24 | `data/models/isolation_forest_v2.pkl`, `data/intermediate/session_scores_v2.csv` |
| Stage 25 | `ai_workspace/reports/stage_25_evaluation_report_v2.md`, plot PNGs |
| Stage 26 | `data/models/hdfs_supervised_best_v2.pkl`, `data/intermediate/hdfs_supervised_scores_v2.csv` |

---

## 7. Log Locations

| Log Source | Location |
|------------|----------|
| Stage 22 execution log | `ai_workspace/logs/stage_22_template_mining.log` |
| Stage 23 execution log | `ai_workspace/logs/stage_23_sequence_v2.log` |
| Stage 24 execution log | `ai_workspace/logs/stage_24_baseline_model_v2.log` |
| API runtime log | stdout (structured JSON via `logging.json` format) |
| Docker API log | `docker compose logs api` |
| Prometheus data | Docker volume (in-container) |
| Alert outbox (dry run) | `artifacts/n8n_outbox/*.json` |

### 7.1 Log Level Configuration

API log level is controlled via standard Python `logging` configuration in `src/observability/logging.py`.
Set `LOG_LEVEL=DEBUG` environment variable for verbose output.

---

## 8. Monitoring Components

### 8.1 Prometheus Metrics (exposed at GET /metrics)

| Metric | Type | Description |
|--------|------|-------------|
| `ingest_events_total` | Counter | Total events POSTed to /ingest |
| `ingest_windows_total` | Counter | Total inference windows emitted |
| `alerts_total` | Counter | Alerts fired, labelled by severity |
| `ingest_errors_total` | Counter | Unhandled errors in /ingest handler |
| `ingest_latency_seconds` | Histogram | End-to-end /ingest handler latency |
| `scoring_latency_seconds` | Histogram | ML model scoring latency per window |

### 8.2 Grafana Dashboard (stage08_api_observability)

Access at http://localhost:3000 (admin/admin after `docker compose up`).

| Panel | Query | Description |
|-------|-------|-------------|
| Events Rate | `rate(ingest_events_total[1m])` | Events per second |
| Windows Rate | `rate(ingest_windows_total[1m])` | Windows per second |
| Alerts by Severity | `rate(alerts_total[1m])` | Stacked by severity label |
| Ingest Latency p95 | `histogram_quantile(0.95, ingest_latency_seconds)` | 95th percentile latency |
| Scoring Latency p95 | `histogram_quantile(0.95, scoring_latency_seconds)` | Model scoring 95th percentile |

### 8.3 Health Endpoint

- `GET /health` returns status: `healthy` / `degraded` / `unhealthy`
- Can be used as a Kubernetes readiness/liveness probe
- Checks: inference engine artifacts loaded, alert manager available, buffer not overflowing

---

## 9. Observability Setup

### 9.1 Prometheus Configuration

File: `prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "anomaly-api"
    static_configs:
      - targets: ["api:8000"]
    metrics_path: /metrics
```

Prometheus scrapes the API every 15 seconds. Metrics are retained for 7 days.

### 9.2 Grafana Provisioning

| File | Purpose |
|------|---------|
| `grafana/provisioning/datasources/datasource.yml` | Auto-connects to Prometheus |
| `grafana/provisioning/dashboards/dashboards.yml` | Watches dashboard directory |
| `grafana/dashboards/stage08_api_observability.json` | Pre-built 5-panel dashboard |

No manual configuration is required — the Grafana instance is fully provisioned at startup.

---

## 10. Runtime Stability Considerations

### 10.1 Memory Usage

| Operation | Peak Memory |
|-----------|------------|
| Stage 22 (template mining, 1M rows) | ~470 MB |
| Stage 23 (sequence building) | ~1138 MB |
| Stage 24 v2 (IsolationForest training, 407 features) | ~2528 MB |
| Stage 26 (LogReg, full HDFS 404K x 404) | ~4344 MB |
| API runtime (no models loaded) | ~200 MB |
| API runtime (models loaded, baseline mode) | ~600 MB |

Large pipeline stages should be run on machines with at least 6 GB available RAM.

### 10.2 Sequence Buffer LRU

The `SequenceBuffer` maintains up to 5000 active stream keys in memory. Streams inactive beyond
LRU capacity are evicted. For high-cardinality workloads (many unique service:session_id pairs),
consider tuning `max_keys` via the `InferenceEngine` constructor.

### 10.3 Alert Ring Buffer

The alert buffer is an in-memory `deque(maxlen=200)`. Alerts are not persisted to disk.
On API restart, the alert history is lost. For production use, integrate a durable storage backend.

### 10.4 Model File Dependencies

The API starts and remains functional without model files — it logs warnings and falls back
to synthetic scoring (when `DEMO_MODE=true`). In production mode without model files,
the inference engine returns risk_score=0.0 (no alerts will fire).

---

## 11. Deployment Readiness Evaluation

### Readiness Scorecard

| Category | Status | Notes |
|----------|--------|-------|
| Containerization | Ready | Dockerfile + docker-compose.yml verified |
| Health checks | Ready | GET /health endpoint + Docker HEALTHCHECK |
| Observability | Ready | Prometheus + Grafana provisioned |
| Authentication | Ready | X-API-Key middleware |
| CI/CD | Ready | GitHub Actions (lint + test + security + docker) |
| Test coverage | Ready | 211 fast tests pass in CI without model files |
| Configuration management | Ready | All params via env vars, .env.example provided |
| Demo mode | Ready | DEMO_MODE=true enables full demo without ML models |
| Alert deduplication | Ready | Per-stream cooldown implemented |
| Documentation | Ready (this audit) | Architecture, runbook, demo script |
| Model retraining | Not automated | Manual batch scripts only |
| Distributed state | Not implemented | Single-node only |
| Persistent alert storage | Not implemented | In-memory ring buffer only |
| HTTPS / TLS | Not configured | Requires reverse proxy (nginx, traefik) |
| Rate limiting | Not implemented | No per-client request throttling |
| Horizontal scaling | Not ready | Stateful in-process sequence buffer |

### Summary

The system is **ready for single-node demo and development deployments**. For production at scale,
the main gaps are: persistent alert storage, model retraining automation, TLS termination, rate
limiting, and distributed state management for the sequence buffer. These are all architectural
extensions rather than bugs.
