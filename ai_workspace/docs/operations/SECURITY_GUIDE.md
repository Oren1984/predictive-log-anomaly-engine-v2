# Security Guide
## Predictive Log Anomaly Engine

---

## Authentication Model

The API uses **X-API-Key header authentication** implemented via `AuthMiddleware` (`src/security/auth.py`).

### How it works

1. Every incoming request is evaluated by `AuthMiddleware` before reaching route handlers.
2. The middleware checks:
   - Is `DISABLE_AUTH=true`? → allow all
   - Does the request path start with a public path prefix? → allow all
   - Does the `X-API-Key` header match `API_KEY`? → allow or deny

### Public paths (no auth required)

By default, the following paths bypass authentication:
- `/health` — liveness/readiness probe
- `/metrics` — Prometheus scrape endpoint
- `/` — observability dashboard SPA
- `/query` — RAG investigation stub

Configure via: `PUBLIC_ENDPOINTS=/health,/metrics,/,/query`

### Configuring the API key

```bash
# .env
API_KEY=your-strong-random-key-here
DISABLE_AUTH=false
```

- If `API_KEY` is empty and `DISABLE_AUTH=false`, the middleware logs a warning and allows all traffic (open mode).
- Never leave `API_KEY` empty in production.

---

## Environment Variable Reference

| Variable | Default | Security Relevance |
|----------|---------|-------------------|
| `API_KEY` | `""` | The expected API key. Must be set in production. |
| `DISABLE_AUTH` | `false` | Set `true` only for local dev/testing. Never in production. |
| `PUBLIC_ENDPOINTS` | `/health,/metrics` | Add paths that must remain unauthenticated (e.g., health probes). |

---

## Production Hardening

### 1. Never disable auth in production
```bash
DISABLE_AUTH=false  # must be false
API_KEY=<strong-random-key>
```

### 2. Use a strong API key
Generate with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Run behind a reverse proxy with TLS
The API server (`uvicorn`) does not terminate TLS. In production:
- Put Nginx or a cloud load balancer in front
- Enforce HTTPS at the proxy layer
- Set `ALLOWED_HOSTS` restrictions at the proxy

### 4. Do not expose Prometheus metrics publicly
`/metrics` is on the public path list by default to allow Prometheus scraping inside Docker. In a production deployment with external network exposure:
- Remove `/metrics` from `PUBLIC_ENDPOINTS`
- Restrict access to the Prometheus port at the network level
- Or scrape from within the same Docker network (preferred)

### 5. Secret management
- Never commit `.env` to version control (it is in `.gitignore`)
- In Kubernetes: use Secrets
- In Docker Swarm: use Docker Secrets
- Locally: use `.env` file

### 6. API_KEY in docker-compose
The demo `docker-compose.yml` uses `DISABLE_AUTH=true`. When deploying for real use:
```yaml
environment:
  - DISABLE_AUTH=false
  - API_KEY=${API_KEY}   # inject from host .env
```

---

## Auth Middleware Implementation Notes

- Middleware is applied globally in `create_app()` (`src/api/app.py`)
- Auth check uses constant-time string comparison implicitly via Python `!=`
- For higher-security deployments, consider adding `hmac.compare_digest` for timing-safe comparison
- No rate limiting is currently implemented — add at the reverse proxy layer for production use

---

## Known Limitations

| Limitation | Mitigation |
|------------|-----------|
| Single shared API key (no per-client keys) | Rotate regularly; restrict network access |
| No rate limiting in the API layer | Implement at reverse proxy (Nginx `limit_req`, AWS WAF, etc.) |
| No TLS at the server | Always deploy behind TLS-terminating proxy |
| In-memory auth state | Restart-safe (key comes from env on each startup) |
