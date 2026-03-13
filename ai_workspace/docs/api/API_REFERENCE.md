# API Reference
## Predictive Log Anomaly Engine

**Base URL:** `http://localhost:8000`
**Auth:** `X-API-Key` header required on all non-public endpoints.

---

## Authentication

All endpoints except `/health`, `/metrics`, `/`, and `/query` require a valid API key in the `X-API-Key` header.

```http
X-API-Key: <your-api-key>
```

Returned when key is missing or incorrect:
```json
{"detail": "Invalid or missing X-API-Key header"}
```
**Status:** `401 Unauthorized`

Auth is controlled by environment variables:
| Variable | Effect |
|----------|--------|
| `API_KEY` | The expected key value |
| `DISABLE_AUTH=true` | Bypass all auth checks |
| `PUBLIC_ENDPOINTS` | Comma-separated path prefixes that skip auth (default: `/health,/metrics`) |

---

## Endpoints

### POST /ingest

Feed a single tokenised log event into the inference pipeline.

**Request body** (`application/json`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `service` | string | Yes | Service/component name (e.g. `"hdfs"`, `"bgl"`) |
| `token_id` | integer | Yes | Template token ID (offset-2 encoded) |
| `timestamp` | float | No (default: 0.0) | Unix epoch of the event |
| `session_id` | string | No (default: `""`) | Session or block identifier |
| `label` | integer\|null | No | Ground-truth label — `0`=normal, `1`=anomaly (for evaluation only) |

**Example request:**
```json
{
  "service": "hdfs",
  "session_id": "blk_-1",
  "token_id": 42,
  "timestamp": 1700000000.0
}
```

**Response** (`200 OK`):

| Field | Type | Description |
|-------|------|-------------|
| `window_emitted` | bool | `true` when a scoring window was emitted |
| `risk_result` | object\|null | Present when `window_emitted=true` |
| `alert` | object\|null | Present when an anomaly was detected and cooldown cleared |

**`risk_result` object:**
| Field | Type | Description |
|-------|------|-------------|
| `stream_key` | string | `"<service>:<session_id>"` |
| `timestamp` | float | Timestamp of last event in window |
| `model` | string | Model that scored the window (`"baseline"`, `"transformer"`, `"ensemble"`) |
| `risk_score` | float | Anomaly score (higher = more anomalous) |
| `is_anomaly` | bool | True when score exceeds model threshold |
| `threshold` | float | Decision threshold used |
| `evidence_window` | object | Window metadata (tokens, timestamps, templates) |

**`alert` object:**
| Field | Type | Description |
|-------|------|-------------|
| `alert_id` | string | UUID v4 |
| `severity` | string | `"critical"`, `"high"`, `"medium"`, or `"low"` |
| `service` | string | Service name |
| `score` | float | Anomaly score |
| `timestamp` | float | Unix epoch |
| `evidence_window` | object | `{templates_preview, token_count, start_ts, end_ts}` |
| `model_name` | string | Scoring model |
| `threshold` | float | Decision threshold |
| `meta` | object | Extra info (`stream_key`, `is_anomaly`, …) |

**Error responses:**
| Status | Condition |
|--------|-----------|
| `401` | Missing or invalid X-API-Key |
| `500` | Internal pipeline error (detail in body) |
| `503` | Pipeline not yet initialised |

---

### GET /alerts

Return the most recent alerts from the in-memory ring buffer (up to `ALERT_BUFFER_SIZE`, default 200).

**Response** (`200 OK`):
```json
{
  "count": 3,
  "alerts": [
    {
      "alert_id": "...",
      "severity": "high",
      "service": "hdfs",
      "score": 1.45,
      "timestamp": 1700000000.0,
      "evidence_window": {...},
      "model_name": "ensemble",
      "threshold": 1.0,
      "meta": {}
    }
  ]
}
```

Alerts are returned oldest-first (FIFO within the ring buffer).

---

### GET /health

Liveness and readiness probe. Always public (no auth required).

**Response** (`200 OK`):
```json
{
  "status": "healthy",
  "uptime_seconds": 42.7,
  "components": {
    "inference_engine": "healthy",
    "alert_manager": "healthy"
  }
}
```

Status values: `"healthy"` | `"degraded"` | `"unhealthy"` | `"unknown"`

---

### GET /metrics

Prometheus text-format metrics. Always public (no auth required).

Returns `text/plain; version=0.0.4` content with all registered counters and histograms.

See [METRICS_REFERENCE.md](../operations/METRICS_REFERENCE.md) for the full metric catalog.

---

### GET /

Returns the observability SPA (`templates/index.html`). Always public.

The SPA provides:
- Dashboard panel (live metrics)
- Alerts panel (recent alerts from ring buffer)
- Investigation panel (query interface)
- Health panel (component status)
- Metrics panel (raw Prometheus text)

---

### POST /query

Keyword-based RAG stub for log investigation. Always public.

**Request body:**
```json
{"query": "what causes block not found errors"}
```

**Response:**
```json
{
  "answer": "Block not found errors typically indicate...",
  "sources": ["doc_id_1", "doc_id_2"]
}
```

---

## Environment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Port |
| `API_KEY` | `""` | Expected key in X-API-Key header |
| `DISABLE_AUTH` | `false` | Set `true` to bypass all auth |
| `PUBLIC_ENDPOINTS` | `/health,/metrics` | Paths that skip auth |
| `METRICS_ENABLED` | `true` | Enable `/metrics` endpoint |
| `MODEL_MODE` | `ensemble` | `baseline` \| `transformer` \| `ensemble` |
| `WINDOW_SIZE` | `50` | Rolling window size (events) |
| `STRIDE` | `10` | Window emission stride |
| `ALERT_BUFFER_SIZE` | `200` | Max alerts in ring buffer |
| `ALERT_COOLDOWN_SECONDS` | `60.0` | Per-stream cooldown (0 = always fire) |
