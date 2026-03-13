# UI Architecture Summary

## Overview

The Phase 8 UI is a single-file SPA (Single-Page Application) served by the existing
FastAPI `ui_router` at `GET /`. It connects exclusively to read-only backend endpoints.

```
Browser
  |
  |  GET /
  v
FastAPI (src/api/ui.py)
  |  HTMLResponse(templates/index.html)
  v
Single-Page App (vanilla HTML/CSS/JS)
  |
  |-- GET  /health   --> Health section + dashboard stat card
  |-- GET  /alerts   --> Alerts section + dashboard mini-table
  |-- GET  /metrics  --> Metrics section + dashboard counters
  |-- POST /query    --> Investigation section
```

---

## Component Map

```
templates/index.html
  |
  +-- <header>         Sticky top bar: title, subtitle, live health dot
  |
  +-- <nav.tabs>       5-tab navigation row
  |     section-dashboard
  |     section-alerts
  |     section-investigation
  |     section-health
  |     section-metrics
  |
  +-- <main>           Section container (only active section visible)
  |
  +-- <footer>         Last-refresh timestamp
  |
  +-- <script>
        state{}              Shared data store (alerts[], health{}, metricsText)
        init()               Boot: refreshAll() + pingQuery() + startAutoRefresh()
        refreshAll()         Parallel fetch: health + alerts + metrics
        renderDashboard()    Populates stat cards, severity bar, recent alerts
        renderAlertsTable()  Full table with severity filter
        renderHealth()       Badge, uptime, components, raw JSON
        renderMetrics()      Parse Prometheus text, populate counters + latency
        runQuery()           POST /query, display answer + sources
        showTab(name)        Toggle visible section
        parsePromMetric()    Extract scalar value from Prometheus text
        parsePromMetricLabel() Extract labelled counter from Prometheus text
```

---

## Data Flow per Section

### Dashboard
```
refreshAll()
  fetchHealth()  -> state.health
  fetchAlerts()  -> state.alerts[]  (reversed: newest first)
  fetchMetrics() -> state.metricsText
    |
renderDashboard()
  parsePromMetric(metricsText, "ingest_events_total")    -> Events card
  parsePromMetric(metricsText, "ingest_windows_total")   -> Windows card
  state.alerts.length                                    -> Alerts card
  state.health.status                                    -> Health card
  parsePromMetricLabel(..., "critical/high/medium/low")  -> Severity bar
  state.alerts.slice(0, 5)                               -> Recent table
```

### Alerts
```
fetchAlerts() -> state.alerts[]
renderAlertsTable()
  filter by alertFilter ("all" | "critical" | "high" | "medium" | "low")
  render <table> rows
```

### Investigation
```
User types question -> runQuery()
  POST /query { question }
  -> QueryResponse { answer, sources[] }
  render answer-box + source-item cards
```

### Health
```
fetchHealth() -> state.health { status, uptime_seconds, components{} }
pingQuery()   -> ep-query status
renderHealth()
  health.status         -> badge class
  health.uptime_seconds -> fmtUptime() display
  health.components     -> component-card grid
  JSON.stringify(health) -> raw-box collapsible
```

### Metrics
```
fetchMetrics() -> state.metricsText (Prometheus text format)
renderMetrics()
  parsePromMetric(t, "ingest_events_total")        -> Events card
  parsePromMetric(t, "ingest_windows_total")       -> Windows card
  parsePromMetric(t, "ingest_errors_total")        -> Errors card
  parsePromMetricLabel(t, ..., "critical")         -> crit count
  parsePromMetricLabel(t, ..., "high")             -> high count
  parsePromMetricLabel(t, ..., "medium")           -> med count
  parsePromMetricLabel(t, ..., "low")              -> low count
  sum/count histograms                             -> avg latency
  state.metricsText                                -> raw-box collapsible
```

---

## Backend Endpoints Consumed (read-only)

| Endpoint    | Method | Response schema                              | Consumer                 |
|-------------|--------|----------------------------------------------|--------------------------|
| `/`         | GET    | `text/html` — this file                      | Browser                  |
| `/health`   | GET    | `HealthResponse{status, uptime_seconds, components}` | Health, Dashboard |
| `/alerts`   | GET    | `AlertListResponse{count, alerts[]}`         | Alerts, Dashboard        |
| `/metrics`  | GET    | Prometheus text format                       | Metrics, Dashboard       |
| `/query`    | POST   | `QueryResponse{answer, sources[]}`           | Investigation            |

No backend files were modified. No new backend routes were added.

---

## Technology Choices

| Concern           | Choice                        | Reason                              |
|-------------------|-------------------------------|-------------------------------------|
| Framework         | None (vanilla HTML/JS/CSS)    | Zero build toolchain, fast load     |
| Charts            | CSS (stacked bar segments)    | No external chart library needed    |
| Styling           | Inline CSS                    | Self-contained single file          |
| Font              | System font stack             | No external requests                |
| Refresh strategy  | Polling (30s interval)        | Simple, no WebSocket complexity     |
| Prometheus parse  | Regex on text format          | Native JS, no parser library        |
| State management  | Plain `state` object          | No framework overhead               |

---

## Security Properties

- Read-only: no form submissions that mutate backend state
- No config values exposed in UI
- No destructive buttons (no delete, reset, clear)
- Auth passthrough: respects existing `AuthMiddleware` (`X-API-Key`)
  — public endpoints (`/`, `/query`, `/health`, `/metrics`) are auth-exempt by default
- No third-party JS loaded from CDN
- No cookies or localStorage used
