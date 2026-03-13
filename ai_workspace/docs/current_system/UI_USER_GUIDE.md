# UI User Guide — Predictive Log Anomaly Engine

## Opening the Dashboard

Start the API server:

```bash
# Development (no Docker)
python main.py

# With Docker (recommended for full stack: API + Prometheus + Grafana)
docker compose up
```

Open in your browser:

```
http://localhost:8000/
```

No login required with default settings (`DISABLE_AUTH=true` or `/` in `PUBLIC_ENDPOINTS`).

---

## Navigation

Five tabs are available across the top navigation bar:

| Tab            | Description                                 |
|----------------|---------------------------------------------|
| Dashboard      | System summary and recent alert activity    |
| Alerts         | Full anomaly alert history and details      |
| Investigation  | AI-powered query interface (RAG)            |
| Health         | System status and component readiness       |
| Metrics        | Live observability counters and latency     |

The header shows a live status indicator (green dot = healthy, amber = degraded, red = unhealthy).

---

## Section Guide

### Dashboard

The main landing page. Shows at a glance:

- **Events Processed** — total log events ingested via `POST /ingest` since server start
- **Windows Scored** — total sliding windows that the inference engine has scored
- **Total Alerts** — number of anomaly alerts currently in the ring buffer
- **System Health** — current health status with uptime

**Severity Bar** — a stacked colour bar showing the distribution of alert severity
(critical / high / medium / low) based on live Prometheus counters.

**Recent Alerts** — the 5 most recent alerts as a compact table. Older alerts are
visible in the full Alerts tab.

The dashboard auto-refreshes every 30 seconds. Click **Refresh** to force an immediate update.

---

### Alerts

A full paginated view of all alerts in the in-memory ring buffer (up to 200 by default).

**Reading each row:**

| Column     | Meaning                                                    |
|------------|------------------------------------------------------------|
| Time (UTC) | When the alert was fired                                   |
| Severity   | critical / high / medium / low based on score/threshold ratio |
| Service    | The event stream key (e.g. `hdfs`, `bgl`)                  |
| Score      | Raw anomaly score from the model                           |
| Threshold  | The model's anomaly threshold at scoring time              |
| Model      | Model name that produced the score                         |
| Alert ID   | Unique identifier for this alert                           |
| Evidence   | Abbreviated JSON of the scored window metadata             |

**Severity logic:**
- `critical` — score / threshold >= 1.5x
- `high` — score / threshold >= 1.2x
- `medium` — score / threshold >= 1.0x (at or above threshold)
- `low` — below threshold but included for informational purposes

**Filtering** — click a severity button (Critical / High / Medium / Low) to filter the table.
Click **All** to return to the full view.

**Note:** Alerts reset on server restart (ring buffer is in-memory).

---

### Investigation

An AI-powered investigation console powered by the built-in RAG knowledge base.

**How to use:**

1. Type a question in the input field (or click a quick-query chip)
2. Press **Enter** or click **Ask**
3. The system returns a direct answer + top-3 source documents

**Quick-query chips** offer one-click access to common questions:
- Alerts — how the alerting policy works
- Model — the anomaly detection model details
- Dataset — HDFS + BGL training data overview
- Threshold — the F1-optimal threshold calculation
- Window — sliding window and stride configuration
- Docker — how to run with Docker Compose
- Prometheus — metrics scraping configuration
- Grafana — dashboard setup and location

**Source documents** show the knowledge base entries that best matched your question,
with a relevance score and a text excerpt.

**What is live vs static:**
- The **answer** and **sources** come from a fixed built-in knowledge base (8 documents).
  They reflect the system design at build time, not real-time runtime state.
- For real-time data (event counts, alert scores, latency), use Dashboard and Metrics.

---

### Health

Displays operational readiness of the system.

**Overall status:**
- `healthy` — all components operational
- `degraded` — one or more components in a reduced state (e.g. model fallback mode)
- `unhealthy` — critical component unavailable

**Uptime** — time elapsed since the API server started.

**Component Status** — each component exposed by `/health` (e.g. model loaded, alert manager
ready, inference engine) is shown as a card with a status colour.

**Endpoint Availability** — a live ping of the four main endpoints:
- `/health` (GET)
- `/alerts` (GET)
- `/metrics` (GET)
- `/query` (POST)

Green = OK, Red = unreachable.

**Raw Health Response** — click "Show / Hide raw JSON" to view the full `/health` response
payload for detailed debugging.

---

### Metrics

Live observability counters scraped from the Prometheus `/metrics` endpoint.

**Key counters:**

| Metric                          | Description                           |
|---------------------------------|---------------------------------------|
| Events Ingested                 | `ingest_events_total`                 |
| Windows Scored                  | `ingest_windows_total`                |
| Ingest Errors                   | `ingest_errors_total`                 |
| Alerts by severity              | `alerts_total{severity="..."}`        |

**Latency:**

| Metric                          | Calculation                           |
|---------------------------------|---------------------------------------|
| Ingest latency (avg)            | `ingest_latency_seconds_sum / _count` |
| Scoring latency (avg)           | `scoring_latency_seconds_sum / _count`|

**Observability Stack:**

When running `docker compose up`, the full stack is available:

| Service    | URL                   | Credentials |
|------------|-----------------------|-------------|
| Prometheus | http://localhost:9090 | none        |
| Grafana    | http://localhost:3000 | admin/admin |

The Stage 08 Grafana dashboard shows: event rate, window rate, alerts by severity (stacked),
ingest latency p95, scoring latency p95.

**Raw Prometheus Output** — click "Show / Hide raw /metrics output" to view the full
Prometheus text format for debugging or export.

---

## What Is Live vs Fallback

| Element                     | Live data source              | Fallback state                   |
|-----------------------------|-------------------------------|----------------------------------|
| Events Processed            | GET /metrics (counter)        | -- if metrics disabled           |
| Windows Scored              | GET /metrics (counter)        | -- if metrics disabled           |
| Alert list + count          | GET /alerts                   | Empty if no events ingested      |
| Health status               | GET /health                   | "Unknown" if unreachable         |
| Component status            | GET /health (components map)  | Empty card grid                  |
| Investigation answers       | POST /query (built-in KB)     | Always available (static KB)     |
| Severity bar                | GET /metrics (label counters) | Empty bar if no alerts fired     |

---

## Demo Flow (Recommended)

1. Start server in demo mode: `DEMO_MODE=true docker compose up`
2. Open `http://localhost:8000/`
3. Visit **Dashboard** — note zero counts initially
4. Use curl or the scripts to inject events:
   ```bash
   curl -s -X POST http://localhost:8000/ingest \
     -H "Content-Type: application/json" \
     -d '{"service":"hdfs","token_id":42}'
   ```
5. Return to **Dashboard** and click **Refresh** — events and alerts appear
6. Visit **Alerts** to inspect individual alerts with severity badges
7. Visit **Investigation** and ask: *"How does the alert threshold work?"*
8. Visit **Health** to confirm all components are ready
9. Visit **Metrics** to see live counters and latency numbers

---

## Troubleshooting

**Dashboard shows "--" for all stats**
- Metrics endpoint may be disabled (`METRICS_ENABLED=false`) or not yet producing data
- Ensure at least a few events have been ingested

**Alerts tab is empty**
- No events have been processed yet, or DEMO_MODE is not set
- In production mode, models must be loaded for windows to be scored and alerts to fire

**Health shows "Unknown"**
- API server is not reachable at the expected host/port
- Check that the server is running (`python main.py` or `docker compose up`)

**Investigation answers seem generic**
- The RAG system uses keyword matching over a fixed knowledge base
- Try more specific keywords: "threshold", "BGL", "IsolationForest", "docker"
