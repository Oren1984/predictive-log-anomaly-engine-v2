# Demo Script

**Project:** Predictive Log Anomaly Engine
**Audience:** Technical (engineers, data scientists, platform teams)
**Duration:** 15-20 minutes
**Date:** 2026-03-04

---

## Pre-Demo Checklist

Before starting the demo, verify:

- [ ] Docker and Docker Compose installed and running
- [ ] Repository cloned and dependencies available
- [ ] `docker compose up -d --build` completed successfully
- [ ] http://localhost:8000/health returns `{"status":"healthy",...}`
- [ ] http://localhost:3000 accessible (Grafana, admin/admin)
- [ ] Terminal open in repository root

```bash
# Quick pre-check
curl -s http://localhost:8000/health | python -m json.tool
```

---

## Section 1: Project Introduction (2 minutes)

### Talking Points

> "This project is a **production-grade, real-time log anomaly detection engine**.
> It ingests structured log events as a stream, maintains rolling context windows per
> log source, scores each window using machine learning models, and fires severity-classified
> alerts — all through a REST API with built-in observability."

### Problem Statement

Modern distributed systems produce millions of log events per day. Manually monitoring them
is impossible. This engine provides:

1. **Automated anomaly detection** — distinguishes normal from abnormal event sequences
2. **Real-time streaming** — processes events as they arrive, not in batch
3. **Explainable results** — every alert includes the evidence window that triggered it
4. **Operational observability** — Prometheus metrics and Grafana dashboards out of the box

### Dataset Used

The system was trained and evaluated on two standard research datasets:

| Dataset | Source | Events | Anomaly Rate |
|---------|--------|--------|-------------|
| **HDFS** | Hadoop Distributed File System logs | ~11.2M | 2.35% |
| **BGL** | BlueGene/L supercomputer logs | ~4.7M | 55.8% |

---

## Section 2: System Architecture Overview (3 minutes)

### Show the Pipeline Diagram

```
Raw Logs (HDFS + BGL)  →  Template Mining  →  Sequence Building
         ↓
IsolationForest (BGL: F1=0.965)  +  LogReg-L2 (HDFS: F1=0.252)
         ↓
Runtime Inference Engine (sliding window, streaming, 3 modes)
         ↓
Alert Manager (severity: critical/high/medium/low, dedup cooldown)
         ↓
REST API  →  Prometheus  →  Grafana Dashboard
```

### Key Design Decisions to Highlight

**1. Template-based tokenization (Stage 22)**
Log messages are normalized to templates using 9 regex substitutions. This reduces the
vocabulary from millions of unique strings to 7,833 templates, enabling statistical modeling.

**2. Session-level feature engineering (Stage 23)**
Rather than modeling individual events, the system models event *sequences* per session —
capturing behavioral patterns like unusual template transitions and entropy changes.

**3. Three scoring modes (Stage 5)**
- `baseline`: Fast IsolationForest on 407 session features
- `transformer`: Next-token prediction using a small Transformer
- `ensemble`: Normalized combination of both (default in production)

**4. Demo Mode (Stage 8/9)**
The system can run a fully functional demo without any trained model files. `DEMO_MODE=true`
uses a configurable synthetic score, enabling CI testing and live demonstrations.

---

## Section 3: Running the Pipeline (5 minutes)

### 3.1 Start the Stack

```bash
docker compose up -d --build
```

Show the three services starting:
- `api` — anomaly detection API on port 8000
- `prometheus` — metrics collection on port 9090
- `grafana` — dashboards on port 3000

```bash
# Watch startup logs
docker compose logs -f api
```

Point out the warmup message indicating synthetic events are being ingested:
```
INFO: Demo warmup: ingesting 75 synthetic events
INFO: Warmup complete: 75 events ingested
```

### 3.2 Verify the API is Live

```bash
curl http://localhost:8000/health | python -m json.tool
```

Expected output:
```json
{
  "status": "healthy",
  "uptime_seconds": 12.3,
  "components": {
    "inference_engine": {"status": "healthy", "artifacts_loaded": false},
    "alert_manager": {"status": "healthy"},
    "alert_buffer": {"status": "healthy", "size": 8}
  }
}
```

Note that `artifacts_loaded: false` is expected in demo mode — the synthetic scorer is active.

### 3.3 Ingest Events via API

```bash
# Ingest a single event
curl -s -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-03-04T10:00:00Z",
    "service": "web-server",
    "session_id": "demo-session-1",
    "token_id": 42,
    "label": 1
  }' | python -m json.tool
```

First few events return `"window_emitted": false` — the buffer is filling up.

```bash
# Ingest enough events to trigger a window (WINDOW_SIZE=5 in demo mode)
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8000/ingest \
    -H "Content-Type: application/json" \
    -d "{\"service\":\"web-server\",\"session_id\":\"demo-session-1\",\"token_id\":$i,\"label\":1}"
done
```

Show a response with `"window_emitted": true` and an alert:
```json
{
  "window_emitted": true,
  "risk_result": {
    "model": "ensemble",
    "risk_score": 2.0,
    "is_anomaly": true,
    "threshold": 1.0
  },
  "alert": {
    "severity": "critical",
    "score": 2.0
  }
}
```

### 3.4 Query Recent Alerts

```bash
curl -s http://localhost:8000/alerts | python -m json.tool
```

Expected output showing alert list with severities and evidence windows.

### 3.5 Quick In-Process Demo (Alternative)

If Docker is unavailable, use the in-process demo:

```bash
python scripts/demo_run.py
```

This runs the full pipeline (ingest -> score -> alert -> query) in ~0.5 seconds using
`TestClient` — no server required.

---

## Section 4: Showing Generated Results (3 minutes)

### 4.1 Offline Pipeline Results

Show the evaluation reports to demonstrate model quality:

```bash
# Stage 22: Template mining results
cat ai_workspace/reports/stage_22_template_report.md
# 7,833 unique templates; elapsed 9.2s

# Stage 25: Evaluation results
cat ai_workspace/reports/stage_25_evaluation_report_v2.md
# BGL F1=0.965, HDFS F1=0.047 (unsupervised), overall PR-AUC=0.2127

# Stage 26: Supervised HDFS results
cat ai_workspace/reports/stage_26_hdfs_supervised_report_v1.md
# LogReg-L2 PR-AUC=0.2334, F1=0.252 (vs unsupervised 0.047)
```

### 4.2 Test Suite Results

```bash
pytest -m "not slow" -v 2>&1 | tail -20
# 211 passed in ~12 seconds
```

Highlight that all tests run without any trained model files.

### 4.3 Demo UI

Open http://localhost:8000 in a browser.

Walk through the three tabs:

**Tab 1: Ingest**
- Click "Ingest 10 Events"
- Show JSON responses appearing in real time
- Point out `window_emitted: true` and alert severity in the response

**Tab 2: Alerts**
- Click "Refresh Alerts"
- Show the alert table with severity-color-coded rows
- Point out timestamp, service, score, and evidence window summary

**Tab 3: RAG Ask**
- Type: "What thresholds does the system use?"
- Click "Ask"
- Show the answer and source documents returned from the built-in knowledge base

---

## Section 5: Observability and Monitoring (3 minutes)

### 5.1 Prometheus Raw Metrics

```bash
curl -s http://localhost:8000/metrics | grep -E "^(ingest|alerts|scoring)"
```

Point out the key metrics:
```
ingest_events_total 85
ingest_windows_total 17
alerts_total{severity="critical"} 12
alerts_total{severity="high"} 3
ingest_latency_seconds_bucket{le="0.01"} 82
scoring_latency_seconds_bucket{le="0.001"} 14
```

### 5.2 Grafana Dashboard

Open http://localhost:3000 (admin/admin).

Navigate to: Dashboards → Stage 08 API Observability.

Walk through the 5 panels:

| Panel | What to Show |
|-------|-------------|
| Events Rate | Events/second ingested (spike after manual ingestion) |
| Windows Rate | Windows/second emitted |
| Alerts by Severity | Stacked bar showing critical vs high vs medium |
| Ingest Latency p95 | End-to-end request latency at 95th percentile |
| Scoring Latency p95 | Model scoring time per window |

Highlight: **all panels auto-populated with zero configuration** thanks to provisioned datasources and dashboards.

### 5.3 Prometheus Target Status

Open http://localhost:9090/targets.

Show the `anomaly-api` target with `State: UP` and the last scrape timestamp.

---

## Section 6: Key Innovation Points (2 minutes)

### 1. Template-Based Normalization
Using regex-based template mining (Stage 22) to abstract 1M diverse log messages into
7,833 canonical templates is the foundational innovation. Without this, statistical modeling
on raw log text is computationally prohibitive.

### 2. Bigram Feature Engineering
Stage 23's inclusion of template transition bigrams (A→B pairs) captures *sequential behavioral
patterns*, not just frequency distributions. This is analogous to n-gram language modeling
applied to system event sequences.

### 3. Three-Mode Ensemble Scoring
The ensemble mode normalizes both baseline and transformer scores by their respective thresholds
before combining, ensuring neither dominates regardless of score scale differences. This is a
principled approach to multi-model fusion.

### 4. Demo Mode with Automatic Warmup
The `DEMO_MODE=true` + `DEMO_WARMUP_ENABLED=true` combination allows the system to be live and
showing alerts within seconds of starting, without any ML model files. This dramatically reduces
the barrier to demonstrating the system.

### 5. Production-Grade API from Day One
The API layer (Stage 7) was built with production concerns from the start: authentication middleware,
Prometheus metrics, health probes, Pydantic v2 validation, and per-stream alert deduplication.

---

## Section 7: Limitations and Future Improvements (2 minutes)

### Current Limitations

| Limitation | Impact | Severity |
|------------|--------|---------|
| HDFS detection is weak (F1=0.252) | Misses most HDFS anomalies | High |
| No automated model retraining | Models become stale over time | Medium |
| Single-node sequence buffer | Cannot scale horizontally | Medium |
| In-memory alert storage | Alerts lost on restart | Low |
| Transformer trained on 2-3 token sequences | Score inflation in production | Medium |

### Planned Improvements

1. **Online learning** — Incremental model updates as new labeled events arrive
2. **Redis-backed sequence buffer** — Enable horizontal scaling
3. **Alert persistence** — Write alerts to PostgreSQL or Elasticsearch
4. **Template drift detection** — Monitor for novel log patterns not in the training vocabulary
5. **HDFS-specific ensemble** — Combine LogReg-L2 (Stage 26) into the runtime inference path
6. **Retrain pipeline automation** — GitHub Actions workflow to retrain on schedule or data drift

### Closing Statement

> "The system demonstrates a complete end-to-end ML engineering workflow: from raw data
> to production-ready API. The architecture is modular, observable, and containerized.
> The immediate next step is improving HDFS anomaly recall by integrating the supervised
> model into the runtime inference path."

---

## Appendix: Demo Commands Quick Reference

```bash
# Start stack
docker compose up -d --build

# Health check
curl http://localhost:8000/health

# Ingest event
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"service":"demo","session_id":"s1","token_id":1,"label":0}'

# Get alerts
curl http://localhost:8000/alerts

# Get metrics
curl http://localhost:8000/metrics

# RAG query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What model is used?"}'

# In-process demo (no server)
python scripts/demo_run.py

# Run tests
pytest -m "not slow"

# Stop stack
docker compose down -v
```
