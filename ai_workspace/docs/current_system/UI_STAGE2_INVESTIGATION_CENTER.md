# UI Stage 2: Investigation Center
## Predictive Log Anomaly Engine

**Status:** Planning / Ready for implementation
**Depends on:** Stage 1 UI (templates/index.html), FastAPI backend (all endpoints live), Prometheus metrics stack
**Role:** AI-assisted read-only investigation interface — NOT a reconfiguration tool

---

## Purpose

Stage 1 UI (current) provides a monitoring dashboard: live metrics, alert feed, basic health status, and a RAG stub for system questions.

Stage 2 upgrades the UI from a **monitoring screen** to an **AI observability investigation center**. The distinction is important:

| Stage 1 (current) | Stage 2 (target) |
|--------------------|-----------------|
| Shows what is happening | Helps understand why it happened |
| Passive metric display | Active anomaly investigation |
| Alert feed (raw list) | Alert investigation with context |
| Static RAG stub (keyword match) | Contextual investigation assistant |
| Single SPA page | Multi-workflow investigation interface |

---

## Core Principle: Read-Only

The Stage 2 UI is **read-only by design**. It does not:
- Reconfigure the inference engine
- Modify alert policies
- Retrain models
- Change any backend state

All user interactions result in GET requests or POST /query calls. The backend is never mutated through the UI.

---

## System Architecture Context

```
┌─────────────────────────────────────────────────────────────────┐
│                         BROWSER (Stage 2 UI)                    │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Alert      │  │  Anomaly     │  │  Investigation       │   │
│  │  Explorer   │  │  Timeline    │  │  Assistant (RAG)     │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                │                     │               │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │ GET /alerts     │ GET /metrics         │ POST /query
          │                │                     │
┌─────────▼────────────────▼─────────────────────▼───────────────┐
│                    FastAPI (src/api/)                           │
│   /alerts   /health   /metrics   /query   /ingest (API only)   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                        │
   ┌──────▼──────┐         ┌───────▼──────┐
   │ Prometheus  │         │   Grafana    │
   │  :9090      │         │   :3000      │
   │ (metrics)   │         │ (dashboards) │
   └─────────────┘         └──────────────┘
```

---

## Workflows

### 1. Alert Investigation Workflow

**User goal:** Understand a fired alert — what happened, when, which service, how severe.

**Flow:**
1. User opens Alert Explorer panel
2. `GET /alerts` returns ring buffer (up to 200 most recent)
3. User selects an alert — sees:
   - `severity`, `service`, `score`, `threshold`, `model_name`
   - `evidence_window`: templates_preview, token_count, start_ts, end_ts
   - `meta.stream_key` — the specific stream that triggered
4. User can ask the Investigation Assistant: "why does this severity level mean?"
5. `POST /query` returns contextual answer from the knowledge base

**What Stage 2 adds:**
- Filterable/sortable alert table (by severity, service, time)
- Alert detail panel (evidence window visualization)
- Quick-link to Grafana time range for the alert timestamp
- Copy `stream_key` for log lookup

### 2. Anomaly Timeline Workflow

**User goal:** See when anomalies occurred relative to normal traffic over time.

**Flow:**
1. Prometheus metrics are parsed from `GET /metrics`
2. `alerts_total{severity=...}` is rendered as a timeline breakdown
3. `ingest_events_total` and `ingest_windows_total` rates show traffic context
4. User can correlate alert spikes with traffic volume
5. Grafana dashboard link jumps to the exact time range for deeper metric exploration

**What Stage 2 adds:**
- Client-side chart rendering of Prometheus metrics (already partially implemented)
- Severity breakdown over selectable time windows (5m / 1h / 24h)
- Correlation view: events ingested vs alerts fired

### 3. Service Health Investigation Workflow

**User goal:** Understand the current component health state and what it means.

**Flow:**
1. `GET /health` returns `status`, `uptime_seconds`, `components`
2. Per-component status cards: inference_engine, alert_manager, alert_buffer
3. `service_health` Prometheus gauge reflects: 1=healthy, 0.5=degraded, 0=unhealthy
4. User sees historical health trend from Prometheus (if recording is configured)

**What Stage 2 adds:**
- Component health cards (not just a single status badge)
- Health history from `service_health` metric
- "What does degraded mean?" → Investigation Assistant answer

### 4. Investigation Assistant Workflow (RAG Upgrade Path)

**Current state (Stage 1):** Keyword-match stub in `src/api/ui.py` with 8 static KB documents.

**Stage 2 target:** Contextual investigation assistant that can answer:
- "What caused the last critical alert?"
- "What is the anomaly score threshold for baseline model?"
- "What does the BGL dataset contain?"
- "How do I interpret the evidence window?"

**Architecture options (choose one for Stage 2):**

| Option | Description | Complexity |
|--------|-------------|-----------|
| A. Expanded static KB | Add 20–30 documents covering all system aspects | Low |
| B. LLM via Anthropic API | Replace keyword match with claude-haiku-4-5 + system prompt | Medium |
| C. Semantic search over KB | Embed KB documents + query embedding similarity | Medium |

**Recommended path for Stage 2:** Option B — LLM via Anthropic API with the existing `/query` endpoint. The endpoint already accepts `{"question": "..."}` and returns `{answer, sources}`. Replacing `_best_answer()` in `src/api/ui.py` with an Anthropic API call requires no schema changes.

---

## Current UI Inventory (Stage 1)

The existing SPA (`templates/index.html`) already provides:

| Section | ID | Current capability |
|---------|----|--------------------|
| Dashboard | `section-dashboard` | Live metrics from GET /metrics (parsed via JS) |
| Alerts | `section-alerts` | Real-time alert feed from GET /alerts (auto-refresh 30s) |
| Investigation | `section-investigation` | POST /query RAG stub (keyword-only) |
| Health | `section-health` | GET /health status + component list |
| Metrics | `section-metrics` | Raw Prometheus text display |

---

## Stage 2 Implementation Boundaries

### What Stage 2 DOES:
- Enhance the existing `templates/index.html` SPA with richer investigation views
- Add alert detail panel with evidence window rendering
- Add timeline/severity visualization using Prometheus data
- Upgrade the Investigation Assistant (POST /query) to LLM-backed responses
- Add filterable/sortable alert table

### What Stage 2 does NOT do:
- Add new API endpoints (all views use existing endpoints)
- Allow user configuration of backend parameters
- Implement user authentication or sessions
- Store investigation notes or user state server-side
- Replace Grafana (Grafana remains the metric deep-dive tool)
- Implement real-time WebSocket streaming (polling is sufficient)

---

## Data Sources Available to Stage 2 UI

| Data | Source | Update frequency |
|------|--------|-----------------|
| Recent alerts (ring buffer) | `GET /alerts` | On demand / 30s auto-refresh |
| Service health + components | `GET /health` | On demand / 30s auto-refresh |
| Prometheus metrics (all) | `GET /metrics` (Prometheus text) | On demand / 15s scrape cadence |
| Contextual answers | `POST /query` | On demand (user-triggered) |
| Grafana dashboards | External link to `:3000` | Real-time in Grafana tab |

---

## Next Steps for Implementation

1. **Expand Investigation Assistant KB** (`src/api/ui.py` — `_KB` and `_ANSWERS` dicts)
   - Add: evidence window explanation, severity classification, model performance metrics, deployment guide snippets

2. **Alert detail panel** (`templates/index.html`)
   - Render `evidence_window.templates_preview` as a log snippet
   - Show score vs threshold bar visualization

3. **Severity timeline chart** (`templates/index.html`)
   - Parse `alerts_total{severity=...}` from GET /metrics
   - Render 5-minute bucketed chart using existing `parsePromMetricLabel()` JS helper

4. **LLM Investigation Assistant** (optional upgrade — `src/api/ui.py`)
   - Replace `_best_answer()` with Anthropic API call
   - Model: `claude-haiku-4-5-20251001` (fast, cost-effective for Q&A)
   - System prompt: inject current `/health` and recent alerts context

5. **Health component cards** (`templates/index.html`)
   - Render per-component status from `GET /health` → `components` dict

---

## Relationship to Grafana

Stage 2 UI and Grafana are **complementary, not competing**:

| Grafana | Stage 2 UI |
|---------|-----------|
| Metric deep-dive with time range selection | Investigation of specific alert events |
| Historical trend analysis | Recent alert context and evidence |
| Alert rule management (future) | Investigation assistant for understanding alerts |
| Operations team tool | Developer / on-call investigation tool |

The Stage 2 UI links out to Grafana for time-range drill-downs but does not replicate its metric visualization capabilities.
