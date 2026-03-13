
# Docker Runtime Architecture

The runtime system consists of an API service connected to an observability stack.

## Flow

Log Events → API (/ingest) → Runtime Inference → Alerts → Metrics (/metrics)
                               ↓
                         Prometheus scrape
                               ↓
                         Grafana dashboards

## Containers Responsibilities

### API
- Receives events via `/ingest`
- Maintains rolling windows (SequenceBuffer)
- Runs inference and emits alerts
- Exposes metrics and health endpoints

### Prometheus
- Scrapes API metrics on schedule
- Stores time-series metrics for Grafana

### Grafana
- Visualizes Prometheus metrics
- Provides dashboards for runtime monitoring

## Demo Path

1. Start containers
2. Send events to `/ingest`
3. Watch metrics and alerts in Grafana dashboard