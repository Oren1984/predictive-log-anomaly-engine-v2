# Alert System Guide
## Predictive Log Anomaly Engine

---

## Overview

The alert system converts anomaly scoring results into structured alerts with severity classification, per-stream deduplication, cooldown suppression, and optional N8N webhook dispatch.

**Components:**
- `src/alerts/models.py` — `Alert` and `AlertPolicy` data models
- `src/alerts/manager.py` — `AlertManager` (dedup + cooldown logic)
- `src/alerts/n8n_client.py` — N8N webhook client (dry-run by default)
- `src/api/pipeline.py` — ring buffer, connects engine → alerts → N8N

---

## Alert Lifecycle

```
POST /ingest
  -> InferenceEngine.ingest(event)
     -> window emitted (at stride boundary)
        -> AlertManager.emit(risk_result)
           -> policy check (is_anomaly? score above threshold?)
           -> cooldown check (per stream_key)
           -> Alert created + severity classified
           -> N8nWebhookClient.send(alert)   [dry-run: writes to artifacts/n8n_outbox/]
           -> Alert appended to ring buffer
```

No alert is fired if:
1. `risk_result.is_anomaly` is `False`
2. `AlertPolicy.threshold > 0` and `risk_result.risk_score < threshold`
3. The same `stream_key` fired an alert within `cooldown_seconds`

---

## Severity Classification

Severity is assigned by comparing `score / threshold` against configured multipliers:

| Severity | Default multiplier | Condition |
|----------|-------------------|-----------|
| `critical` | 1.5x | `score >= 1.5 * threshold` |
| `high` | 1.2x | `score >= 1.2 * threshold` |
| `medium` | 1.0x | `score >= 1.0 * threshold` |
| `low` | fallback | none of the above matched |

The first matching severity (checked highest-multiplier-first) is used.

---

## Ring Buffer

Recent alerts are kept in an in-memory `deque` with a configurable max size.

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERT_BUFFER_SIZE` | `200` | Maximum alerts retained in buffer |

- Buffer is per-process (not persisted across restarts)
- Oldest alerts are discarded when the buffer is full (FIFO)
- Retrieved via `GET /alerts`

---

## Cooldown (Deduplication)

Per-stream-key cooldown prevents alert storms from the same source.

| Variable | Default | Description |
|----------|---------|-------------|
| `ALERT_COOLDOWN_SECONDS` | `60.0` | Minimum seconds between alerts per stream |

- Set to `0` to disable cooldown (fire on every anomalous window)
- `stream_key` format: `"<service>:<session_id>"`
- Cooldown state is in-memory only (reset on restart)

In the demo docker-compose config, `ALERT_COOLDOWN_SECONDS=0` so every window fires.

---

## N8N Webhook Integration

The `N8nWebhookClient` sends each fired alert as a JSON POST to a webhook URL.

| Variable | Default | Description |
|----------|---------|-------------|
| `N8N_WEBHOOK_URL` | `""` | Target webhook URL |
| `N8N_DRY_RUN` | `true` | When `true`, writes JSON to `artifacts/n8n_outbox/` instead of POSTing |
| `N8N_TIMEOUT_SECONDS` | `5` | HTTP request timeout |

**Dry-run mode (default):** Each alert payload is written to a UUID-named JSON file in `artifacts/n8n_outbox/`. This directory is gitignored and accumulates during test runs.

**Live mode:** Set `N8N_DRY_RUN=false` and provide a valid `N8N_WEBHOOK_URL`. The client sends an HTTP POST with `Content-Type: application/json`.

---

## Alert Payload Schema

```json
{
  "alert_id": "uuid-v4-string",
  "severity": "high",
  "service": "hdfs",
  "score": 1.45,
  "timestamp": 1700000000.0,
  "evidence_window": {
    "templates_preview": ["template A", "template B"],
    "token_count": 50,
    "start_ts": 1699999950.0,
    "end_ts": 1700000000.0
  },
  "model_name": "ensemble",
  "threshold": 1.0,
  "meta": {
    "stream_key": "hdfs:blk_-1",
    "is_anomaly": true
  }
}
```

---

## Tuning Alerts

**To reduce false positives:**
- Increase `ALERT_COOLDOWN_SECONDS` (e.g., `300`)
- Increase `WINDOW_SIZE` (larger windows = more stable scores)
- Use `MODEL_MODE=ensemble` for best accuracy

**To increase sensitivity:**
- Decrease `ALERT_COOLDOWN_SECONDS` (e.g., `0`)
- Decrease `STRIDE` (more frequent window emissions)
- Use `MODEL_MODE=baseline` in demo mode

**To set a minimum score threshold** (above `is_anomaly`):
Edit `AlertPolicy(threshold=X)` in `src/api/pipeline.py` or extend settings.
