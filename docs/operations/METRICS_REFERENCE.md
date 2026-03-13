# Metrics Reference
## Predictive Log Anomaly Engine

All metrics are exposed at `GET /metrics` in Prometheus text format.

---

## Metric Catalog

### Counters

#### `ingest_events_total`
Total events received by `POST /ingest`.

- **Type:** Counter
- **Labels:** none
- **Incremented:** on every call to `pipeline.process_event()`, regardless of whether a window was emitted

```promql
# Events ingestion rate (per second, 5-minute window)
rate(ingest_events_total[5m])
```

---

#### `ingest_windows_total`
Total scoring windows emitted by `InferenceEngine`.

- **Type:** Counter
- **Labels:** none
- **Incremented:** only when `risk_result is not None` (stride boundary reached)

```promql
# Window emission rate
rate(ingest_windows_total[5m])

# Ratio of events to windows (shows window fill factor)
rate(ingest_events_total[5m]) / rate(ingest_windows_total[5m])
```

---

#### `alerts_total`
Total alerts fired (not suppressed by cooldown).

- **Type:** Counter
- **Labels:** `severity` — one of `critical`, `high`, `medium`, `low`
- **Incremented:** when `AlertManager.emit()` returns a non-empty alert list

```promql
# Alert rate by severity (5-minute window)
rate(alerts_total{severity="critical"}[5m])
rate(alerts_total{severity="high"}[5m])
rate(alerts_total{severity="medium"}[5m])

# Total alert rate across all severities
sum(rate(alerts_total[5m]))
```

---

#### `ingest_errors_total`
Total unhandled errors in the `/ingest` handler.

- **Type:** Counter
- **Labels:** none
- **Incremented:** when `pipeline.process_event()` raises an exception caught in the route handler

```promql
# Error rate
rate(ingest_errors_total[5m])

# Error ratio vs. total ingest calls
rate(ingest_errors_total[5m]) / rate(ingest_events_total[5m])
```

---

### Histograms

#### `ingest_latency_seconds`
End-to-end `POST /ingest` handler latency in seconds.

- **Type:** Histogram
- **Labels:** none
- **Buckets:** 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0 seconds
- **Measured:** from entry of route handler to response return (includes scoring + alert evaluation)

```promql
# p95 ingest latency over 5 minutes
histogram_quantile(0.95, rate(ingest_latency_seconds_bucket[5m]))

# Average ingest latency
rate(ingest_latency_seconds_sum[5m]) / rate(ingest_latency_seconds_count[5m])
```

---

#### `scoring_latency_seconds`
Model scoring latency per window in seconds.

- **Type:** Histogram
- **Labels:** none
- **Buckets:** 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0 seconds
- **Measured:** from `InferenceEngine.ingest()` call start to return (model scoring only)

```promql
# p95 scoring latency
histogram_quantile(0.95, rate(scoring_latency_seconds_bucket[5m]))

# Average scoring latency
rate(scoring_latency_seconds_sum[5m]) / rate(scoring_latency_seconds_count[5m])
```

---

---

#### `service_health`
Application health state, updated by each call to `GET /health`.

- **Type:** Gauge
- **Labels:** none
- **Values:** `1.0` = healthy, `0.5` = degraded, `0.0` = unhealthy
- **Default on startup:** `1.0` (optimistic; updated on first health poll)
- **Set by:** `/health` route handler after `HealthChecker.check()` evaluates components

```promql
# Current health state
service_health

# Alert when degraded or unhealthy
service_health < 1.0
```

---

## Grafana Dashboard

The canonical dashboard (`grafana/dashboards/stage08_api_observability.json`) provides **9 panels** (version 3):

| Panel | Query | Notes |
|-------|-------|-------|
| Events Ingested (5 min window) | `increase(ingest_events_total[5m])` | |
| Scoring Windows (5 min window) | `increase(ingest_windows_total[5m])` | |
| Alerts Fired by Severity (stacked) | `increase(alerts_total{severity=...}[5m])` × 4 | |
| Ingest Latency p95 | `histogram_quantile(0.95, rate(ingest_latency_seconds_bucket[5m]))` | |
| Scoring Latency avg + p95 | avg + p95 | |
| System Health | `service_health` | Reflects actual component health (1/0.5/0) |
| Alert Severity Distribution (all-time) | `sum by (severity)(alerts_total)` | |
| Events Throughput (5 min rolling) | `increase(ingest_events_total[5m])` | |
| Ingest Error Rate (errors/sec) | `rate(ingest_errors_total[5m])` | Added in upgrade pass |

**Datasource UID:** `prometheus-stage8`

---

## Prometheus Configuration

Scrape configuration (`prometheus/prometheus.yml`):
```yaml
scrape_interval: 15s
targets: [api:8000]  # FastAPI service in docker-compose network
```

Alert rules: `prometheus/alerts.yml` — 4 rules:
- `ServiceDown` (critical) — scrape target unreachable for 1 min
- `ServiceUnhealthy` (warning) — `service_health < 1.0` for 2 min
- `HighIngestErrorRate` (warning) — error rate > 0.1/s for 2 min
- `IngestStalled` (warning) — no events ingested for 5 min

Retention: 7 days (demo) / 30 days (prod via docker-compose.prod.yml)

---

## Notes

- Metrics use a **private registry** (`CollectorRegistry()`) per `MetricsRegistry` instance — this prevents `ValueError: Duplicated timeseries` when multiple instances are created in tests.
- No namespace prefix is currently applied to metric names (e.g., no `plae_` prefix). This is safe for single-service deployments but may need a prefix if metrics are federated with other services.
- `MetricsMiddleware` only measures `POST /ingest` latency. Other routes (`GET /health`, `GET /alerts`, etc.) are not instrumented.
