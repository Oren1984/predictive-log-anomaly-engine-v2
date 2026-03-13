# Prometheus Monitoring

Prometheus is responsible for collecting system metrics from the Predictive Log Anomaly Engine.

It periodically scrapes metrics exposed by the API service.

## Metrics Collected

Prometheus collects metrics such as:

- anomaly detection scores
- alert counts
- API request latency
- inference runtime
- system performance metrics

## Integration

Prometheus integrates with:

- FastAPI metrics endpoint
- Grafana dashboards

## Metrics Endpoint

Example:


http://localhost:8000/metrics


## Role in Observability Stack

Prometheus acts as the **metrics storage and collection layer**, while Grafana acts as the **visualization layer**. Prometheus collects and stores the metrics, which Grafana then queries to create dashboards and visualizations for monitoring the system's behavior.