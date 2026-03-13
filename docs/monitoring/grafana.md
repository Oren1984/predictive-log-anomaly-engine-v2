# Grafana Monitoring

Grafana is used as the visualization layer of the observability stack.

It provides dashboards for monitoring the behaviour of the Predictive Log Anomaly Engine.

## Responsibilities

Grafana visualizes:

- anomaly scores
- system alerts
- pipeline runtime metrics
- API request metrics
- model inference behaviour

## Access

Grafana UI:

http://localhost:3000

Dashboard:

http://localhost:3000/d/stage08-api-obs/stage-08-api-observability

## Authentication

Credentials are documented in:

## Admin

User:
admin

Password:
admin

## Data Source

Grafana reads metrics from **Prometheus**, which collects runtime metrics exposed by the API.