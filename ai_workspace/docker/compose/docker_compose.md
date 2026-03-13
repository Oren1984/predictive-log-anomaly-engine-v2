# Docker Compose Configuration

This document describes the Docker Compose setup used to run the **Predictive Log Anomaly Engine** and its observability stack.

The Docker Compose configuration orchestrates multiple containers required for the system.

---

# Services Overview

The compose stack includes the following services:

| Service | Purpose |
|------|------|
| API | Main anomaly detection service |
| Prometheus | Metrics collection |
| Grafana | Monitoring dashboards |

---

# Service Details

## API Service

Responsible for:

- receiving log events
- performing anomaly detection
- generating alerts
- exposing runtime metrics

Example endpoints:


/ingest
/alerts
/health
/metrics


Default access:


http://localhost:8000


---

## Prometheus

Prometheus collects metrics from the API service.

Metrics endpoint:


http://localhost:8000/metrics


Prometheus interface:


http://localhost:9090


Responsibilities:

- scrape metrics
- store time-series data
- provide data source for Grafana

---

## Grafana

Grafana visualizes metrics collected by Prometheus.

Main interface:


http://localhost:3000


Example dashboard:


http://localhost:3000/d/stage08-api-obs/stage-08-api-observability


Credentials are documented in:


monitoring/grafana/grafana_access.md


---

# System Flow

The runtime architecture follows this pipeline:


Log Events
↓
API Service
↓
Anomaly Detection Engine
↓
Metrics Export (/metrics)
↓
Prometheus Scraping
↓
Grafana Dashboards


---

# Running the Stack

From the project root directory:

Build containers:


docker compose build


Start services:


docker compose up


Run in detached mode:


docker compose up -d


Stop services:


docker compose down


---

# Restarting the Stack

If configuration changes were made:


docker compose down
docker compose up --build


---

# Logs

To inspect container logs:


docker compose logs


Follow logs live:


docker compose logs -f


---

# Useful Commands

Restart a single service:


docker compose restart api


Rebuild images:


docker compose build --no-cache


Check running containers:


docker ps


---

# Purpose

Docker Compose provides:

- reproducible environment
- isolated dependencies
- simplified deployment
- integrated observability stack

This ensures the Predictive Log Anomaly Engine can be **easily deployed and demonstrated**.