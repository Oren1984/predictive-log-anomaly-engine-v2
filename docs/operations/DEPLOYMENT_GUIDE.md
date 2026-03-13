# Deployment Guide
## Predictive Log Anomaly Engine

---

## Prerequisites

- Docker 24+ and Docker Compose v2
- Python 3.11+ (for local runs without Docker)
- 2 GB RAM minimum (4 GB recommended for ensemble model)

---

## Quick Start (Docker Compose — Demo Mode)

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd predictive-log-anomaly-engine

# 2. Copy and review environment variables
cp .env.example .env
# Edit .env as needed (safe to run with defaults in demo mode)

# 3. Start the full stack
docker compose up -d

# 4. Verify it's running
curl http://localhost:8000/health

# 5. View the dashboard
open http://localhost:3000   # Grafana (admin/admin)
open http://localhost:8000   # Observability SPA
```

**Services:**
| Service | Port | URL |
|---------|------|-----|
| FastAPI | 8000 | `http://localhost:8000` |
| Prometheus | 9090 | `http://localhost:9090` |
| Grafana | 3000 | `http://localhost:3000` |

---

## Local Run (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default settings
python main.py

# Or run directly with uvicorn
uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

---

## Environment Variables

See `.env.example` for the full list. Key variables for deployment:

### API + Auth
| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Port |
| `API_KEY` | `""` | X-API-Key secret (empty = open) |
| `DISABLE_AUTH` | `false` | Set `true` only for local dev |
| `PUBLIC_ENDPOINTS` | `/health,/metrics` | Paths that skip auth |

### Model
| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_MODE` | `ensemble` | `baseline` \| `transformer` \| `ensemble` |
| `WINDOW_SIZE` | `50` | Rolling window size (events) |
| `STRIDE` | `10` | Window emission stride |

### Demo Mode
| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_MODE` | `false` | Use fallback scorer (no real models needed) |
| `DEMO_SCORE` | `2.0` | Fallback anomaly score (>1.0 = anomaly) |
| `DEMO_WARMUP_ENABLED` | `false` | Ingest synthetic events on startup |
| `DEMO_WARMUP_EVENTS` | `75` | Number of warmup events |

---

## Model Loading

At startup, `Pipeline.load_models()` calls `InferenceEngine.load_artifacts()`:

- **Baseline model** (`models/isolation_forest_v2.pkl`) — IsolationForest
- **Transformer model** (`models/transformer_model.pt`) — LSTM-based
- **Feature extractor** (`data/intermediate/sequences_train.parquet`) — fit on startup

If model files are absent (e.g., in CI), the engine falls back to:
- `DEMO_MODE=true` → returns `DEMO_SCORE` (configurable) for every window
- `DEMO_MODE=false` → returns `0.0` (no anomalies detected)

In docker-compose, models are mounted as a volume:
```yaml
volumes:
  - ./models:/app/models:ro
```

Place trained model files in `./models/` before starting the stack.

---

## Production Deployment (docker-compose.prod.yml)

A production-style override file (`docker-compose.prod.yml`) is provided. It is used **alongside** the base file, not as a replacement.

```bash
# Generate a strong API key
export API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export GRAFANA_ADMIN_PASSWORD="YourStrongPasswordHere"

# Start with production overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**What the prod override changes vs demo defaults:**

| Setting | Demo | Production |
|---------|------|-----------|
| `DISABLE_AUTH` | `true` | `false` |
| `API_KEY` | _(empty)_ | Required from env |
| `DEMO_MODE` | `true` | `false` |
| `WINDOW_SIZE` | `5` | `50` |
| `STRIDE` | `1` | `10` |
| `ALERT_COOLDOWN_SECONDS` | `0` | `60` |
| `ALERT_BUFFER_SIZE` | `200` | `500` |
| Prometheus retention | `7d` | `30d` |
| Grafana admin password | `admin` | From `GRAFANA_ADMIN_PASSWORD` env |
| Grafana anonymous access | _(default)_ | Disabled |

Both `API_KEY` and `GRAFANA_ADMIN_PASSWORD` must be set in the environment or the compose command will fail with a clear error message.

---

## Local Smoke Test

```bash
# Requires Docker to be running
./scripts/smoke_test.sh
```

This script:
1. Starts the stack with `docker compose up -d`
2. Waits for `GET /health` to return 200
3. Verifies `GET /metrics` contains expected metric names
4. Posts 10 events to `POST /ingest`
5. Asserts `GET /alerts` returns at least 1 alert
6. Tears down with `docker compose down`

---

## CI/CD

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs three jobs:

| Job | What it does |
|-----|-------------|
| `tests` | `pytest -m "not slow"` (fast suite, ~12s) |
| `security` | `pip-audit` (dependency vulns) + `trivy` (image scan) |
| `docker` | Build image + compose smoke test + ingest/alert check |

Model-dependent tests are marked `@pytest.mark.slow` and excluded from CI (`pytest -m "not slow"`).

---

## Production Deployment Checklist

- [ ] Set a strong `API_KEY` (32+ random bytes)
- [ ] Set `DISABLE_AUTH=false`
- [ ] Set `DEMO_MODE=false`
- [ ] Mount real trained model files at `./models/`
- [ ] Deploy behind a TLS-terminating reverse proxy (Nginx, Caddy, ALB)
- [ ] Restrict `/metrics` port to the Prometheus scraper network
- [ ] Configure `ALERT_COOLDOWN_SECONDS` for your expected event rate
- [ ] Set `ALERT_BUFFER_SIZE` for your retention requirements
- [ ] Configure `N8N_WEBHOOK_URL` and `N8N_DRY_RUN=false` for live alert dispatch
- [ ] Set Grafana admin password via `GF_SECURITY_ADMIN_PASSWORD`
- [ ] Enable Prometheus persistent storage (`--storage.tsdb.retention.time=30d`)

---

## Health Checks

The `GET /health` endpoint is used by both Docker health checks:

**Dockerfile:** `HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5`

**docker-compose.yml:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 15s
  timeout: 5s
  retries: 5
  start_period: 30s
```

The health response includes `status: "healthy" | "degraded" | "unhealthy"` and per-component status.
