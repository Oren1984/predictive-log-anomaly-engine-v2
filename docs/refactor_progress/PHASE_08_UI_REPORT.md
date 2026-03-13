# Phase 8 — UI Foundation Report

## Objective

Build a professional, read-only Observability & Investigation UI on top of the existing
Predictive Log Anomaly Engine backend (Phases 1–7.5).

The dashboard must:
- Display system status, alert activity, and operational metrics
- Support AI-powered investigation queries
- Remain strictly read-only — no config editing, no destructive actions
- Be demo-ready and presentation-friendly

---

## What Was Implemented

A single-page application (SPA) served at `GET /` that replaces the previous 3-tab
demo panel (Ingest / Alerts / RAG Ask) with a full 5-section observability dashboard.

All sections are purely read-only. No backend configuration is exposed or editable.

---

## Pages / Sections Created

| Section ID             | Tab Label    | Purpose                                                       |
|------------------------|--------------|---------------------------------------------------------------|
| `section-dashboard`    | Dashboard    | Summary stat cards, severity bar, recent alerts mini-table    |
| `section-alerts`       | Alerts       | Full alert table with severity filter, ring buffer display    |
| `section-investigation`| Investigation| RAG query interface, quick-query chips, answer + sources      |
| `section-health`       | Health       | System health badge, uptime, component grid, endpoint status  |
| `section-metrics`      | Metrics      | Live counters, latency averages, raw Prometheus output        |

### Dashboard
- 4 stat cards: Events Processed, Windows Scored, Total Alerts, System Health
- Engine mode badge
- Alert severity breakdown (pills + stacked colour bar)
- Recent 5 alerts mini-table
- Auto-refresh every 30 seconds

### Alerts
- Full table: Time, Severity, Service, Score, Threshold, Model, Alert ID, Evidence
- Severity filter buttons: All / Critical / High / Medium / Low
- Count badge on tab
- Refresh button

### Investigation
- Natural-language query input (`POST /query`)
- Quick-query chips: Alerts, Model, Dataset, Threshold, Window, Docker, Prometheus, Grafana
- Two-column result layout: Answer block + Source documents (id, relevance, snippet)
- Enter key support

### Health
- Overall health status badge (healthy / degraded / unhealthy)
- Uptime display (formatted h/m/s)
- Component grid from `/health` response
- Endpoint availability table (live ping of `/health`, `/alerts`, `/metrics`, `/query`)
- Raw health JSON (collapsible)

### Metrics
- 3 stat cards: Events Ingested, Windows Scored, Ingest Errors
- Alerts by severity (parsed from Prometheus label selectors)
- Average latency: ingest and scoring (sum/count from Prometheus histograms)
- Observability stack info (Prometheus port 9090, Grafana port 3000)
- Raw Prometheus text output (collapsible)

---

## Routes Used

All routes are existing read-only backend endpoints — no new routes were added.

| Route          | Method | Used by                           |
|----------------|--------|-----------------------------------|
| `/`            | GET    | HTML entry point (ui.py)          |
| `/health`      | GET    | Health section, dashboard card    |
| `/alerts`      | GET    | Dashboard recent alerts, Alerts   |
| `/metrics`     | GET    | Metrics section, dashboard stats  |
| `/query`       | POST   | Investigation section             |

---

## Frontend Structure

```
templates/
  index.html          — Single-file SPA (HTML + inline CSS + inline JS, ~600 lines)
```

No external JS/CSS dependencies. No build toolchain required.

### JavaScript Architecture

| Function          | Purpose                                              |
|-------------------|------------------------------------------------------|
| `showTab(name)`   | Tab navigation, section visibility                   |
| `refreshAll()`    | Fetch all 3 endpoints in parallel, re-render active  |
| `fetchHealth()`   | GET /health, updates `state.health`                  |
| `fetchAlerts()`   | GET /alerts, updates `state.alerts` (newest first)   |
| `fetchMetrics()`  | GET /metrics, updates `state.metricsText`            |
| `renderDashboard()` | Populate stat cards, severity bar, recent table    |
| `renderAlertsTable()` | Full alert table with current filter             |
| `renderHealth()`  | Health badge, uptime, components, raw JSON           |
| `renderMetrics()` | Parse Prometheus text, populate counters + latency   |
| `runQuery()`      | POST /query, display answer + sources                |
| `parsePromMetric()` | Extract scalar from Prometheus text format         |
| `parsePromMetricLabel()` | Extract labelled metric (e.g. severity="critical") |

---

## Styling Approach

- Dark observability theme (Grafana / SOC dashboard inspired)
- Background: `#050c1a` (deep navy), cards: `#0d1b2e`, borders: `#1a2d45`
- Accent: `#06b6d4` (cyan-400)
- Severity colours: critical=red, high=orange, medium=amber, low=green
- Severity badges, filter buttons, status dots, component cards
- System-font stack — zero external font loading
- Responsive grid for stat cards and component grid
- Sticky header with live health indicator dot

---

## Backend Additions

**None.** The UI reuses all existing endpoints without modification.

The only backend-adjacent change: `src/api/ui.py` was not modified.

---

## Test Changes

Two existing tests were updated to check for the new section IDs instead of the old
panel IDs (`panel-ingest`, `panel-alerts`, `panel-rag`):

| File                                          | Test changed                          |
|-----------------------------------------------|---------------------------------------|
| `tests/integration/test_smoke_api.py`         | `test_ui_index_contains_expected_sections` |
| `tests/test_pipeline_smoke.py`                | `TestDemoUI.test_ui_has_all_panels`   |

New expected section IDs:
`section-dashboard`, `section-alerts`, `section-investigation`, `section-health`, `section-metrics`

Full test suite: **578 passed, 26 deselected (slow/model-dependent)** — no regressions.

---

## Known Limitations

1. **No live streaming** — data is polled on demand and auto-refreshed every 30s.
   Real-time WebSocket streaming is not implemented.

2. **Metrics require server uptime** — counters start at 0 on each restart; there is
   no persistent metrics store.

3. **Investigation is keyword-based RAG** — the `/query` endpoint uses keyword overlap
   against a fixed 8-document knowledge base, not a vector database or LLM.

4. **No authentication UI** — the dashboard uses the same auth as the backend. If
   `API_KEY` is set and `/` is not in `PUBLIC_ENDPOINTS`, the browser will receive 401.
   Default configuration exposes `/` and `/query` as public.

5. **Grafana / Prometheus** — the links in the Metrics section assume local Docker
   deployment on default ports. They are informational only (not embedded iframes).

---

## Demo Readiness

- Open `http://localhost:8000/` after starting the server
- No login required with default settings
- Dashboard auto-refreshes every 30s
- Recommended demo flow: start with Dashboard -> Alerts -> Metrics -> Health
- For Investigation demo: use quick-query chips or free-form questions
- Docker compose stack (`docker compose up`) pre-configures DEMO_MODE=true for
  alerts without trained model files
