# Docker Environment

The project runs as a containerized system to ensure reproducibility.

## Services (high level)

- **API**: FastAPI service exposing `/ingest`, `/alerts`, `/health`, `/metrics`
- **Prometheus**: collects metrics from the API
- **Grafana**: dashboards for observability

## Run Commands

From the repository root:

```powershell
docker compose build
docker compose up

---

To stop:

docker compose down
Ports

API: http://localhost:8000

Prometheus: http://localhost:9090

Grafana: http://localhost:3000

Notes

If you change monitoring configs, restart services:
docker compose down; docker compose up

If images are stale, rebuild:
docker compose build --no-cache


---