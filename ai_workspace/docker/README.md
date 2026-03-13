# Docker (Project Runtime)

This directory documents how to run the Predictive Log Anomaly Engine using Docker.

**Note:** The actual `Dockerfile` and `docker-compose.yml` are located at the repository root
to follow common Docker conventions.

## What’s here

- `docs/docker_environment.md` — services, ports, and run commands
- `docs/docker_architecture.md` — runtime architecture and container responsibilities
- `compose/` — optional compose overrides (if needed in the future)

## Quick Start (Windows PowerShell)

From the repository root:

```powershell
docker compose build
docker compose up

Access:

API: http://localhost:8000

Grafana: http://localhost:3000

Prometheus: http://localhost:9090


---