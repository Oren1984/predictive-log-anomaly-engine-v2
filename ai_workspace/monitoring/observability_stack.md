# Observability Stack

The Predictive Log Anomaly Engine includes a monitoring and observability stack used to track system behaviour in real time.

## Components

The observability system consists of three layers.

### 1. Metrics Collection

Prometheus collects runtime metrics from the API service.

Metrics include:

- anomaly detection events
- system alerts
- inference runtime
- API request latency

### 2. Visualization

Grafana visualizes the collected metrics through dashboards.

Dashboards allow inspection of:

- anomaly score trends
- system alert frequency
- runtime performance
- pipeline behaviour

### 3. Logging

Application logs are stored under:


ai_workspace/logs/


Logs provide detailed runtime information used for debugging and analysis.

## Architecture

Pipeline → API → Prometheus → Grafana


Log Events
↓
Anomaly Detection Engine
↓
API Metrics Endpoint
↓
Prometheus Scraping
↓
Grafana Dashboards


## Purpose

The observability stack allows:

- monitoring system health
- tracking anomaly detection behaviour
- debugging runtime issues
- validating model performance during live operation