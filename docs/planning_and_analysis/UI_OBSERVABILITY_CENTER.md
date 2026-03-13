# UI Observability Center
## Predictive Log Anomaly Engine — Observability + AI Investigation Center

**Document Type:** UI Development Specification
**Assembled from:**
- `UI_OBSERVABILITY_INVESTIGATION_CENTER.md` — Full document (Sections 1-10)
- `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md` — Section 8 (UI Readiness Review)

The original source documents remain unchanged. This file consolidates all UI architecture, screen specifications, API endpoint schemas, RAG integration design, and technology recommendations into one reference.

---

## Part A: UI Development Specification
*Source: UI_OBSERVABILITY_INVESTIGATION_CENTER.md*

---

# UI Development Specification
## Observability + AI Investigation Center
### Predictive Log Anomaly Engine — Post-OOP Refactor

**Document Type:** Technical Development Specification
**Scope:** UI Layer — Option 2: Observability + AI Investigation Center
**Based on:** `REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md`, `IMPLEMENTATION_ACTION_PLAN.md`
**Date:** 2026-03-07
**Status:** Specification — Ready for Implementation

---

## Table of Contents

1. [Purpose of the UI Layer](#1-purpose-of-the-ui-layer)
2. [System Context](#2-system-context)
3. [UI Architecture](#3-ui-architecture)
4. [UI Screens and Views](#4-ui-screens-and-views)
5. [Required API Endpoints](#5-required-api-endpoints)
6. [RAG Integration](#6-rag-integration)
7. [UI Technology](#7-ui-technology)
8. [Development Phases](#8-development-phases)
9. [Risks and Limitations](#9-risks-and-limitations)
10. [Implementation Recommendations](#10-implementation-recommendations)

---

## 1. Purpose of the UI Layer

The Observability + AI Investigation Center is the presentation and investigation layer of the Predictive Log Anomaly Engine. Its role is strictly read-only: it surfaces data produced by the AI pipeline, the alert management system, and the Prometheus metrics stack. It does not modify system configuration, trigger model retraining, or interact with any write-path component.

The UI addresses a specific operational gap. Once the OOP AI pipeline refactor is complete, the system will produce a rich continuous stream of diagnostic signals: reconstruction error timeseries from the `AnomalyDetector`, severity probability distributions from the `SeverityClassifier`, context vectors from the `SystemBehaviorModel`, and structured alert objects from the `AlertManager`. Without a dedicated investigation interface, these signals are only observable through raw Prometheus metrics and the Grafana infrastructure dashboard, neither of which is designed for alert-level investigation or per-incident diagnosis.

The UI serves two distinct user needs:

**Operational monitoring.** A continuous view of the system's health, current alert state, live anomaly scores, and pipeline component status. This view allows an operator to assess system health at a glance without querying individual API endpoints or reading Grafana panels.

**Alert investigation.** When an alert fires, an operator needs to understand why it fired, what the system was doing in the preceding window, how severe the reconstruction error was, and how similar events have been classified historically. The RAG investigation panel provides this capability by anchoring a natural-language question interface to the selected alert's evidence.

The UI is not a replacement for Grafana. Grafana serves infrastructure-level observability: event throughput, endpoint latency, resource utilization. The Investigation Center serves AI-pipeline-level observability: anomaly explanation, alert evidence, score interpretation, and pipeline state inspection. These two layers are complementary and must coexist.

---

## 2. System Context

The UI layer sits at the top of the system stack, above the API service boundary. It does not communicate directly with any internal component. All data flows through the FastAPI service layer.

```
+----------------------------------+
|  UI Layer                        |
|  Observability + Investigation   |
|  Center (Streamlit / HTML)       |
+----------------------------------+
              |
              | HTTP / WebSocket
              |
+----------------------------------+
|  FastAPI Service (port 8000)     |
|  src/api/app.py                  |
|  src/api/routes.py               |
|  src/api/ui.py                   |
+----------------------------------+
       |              |
       |              +---------------------------+
       |                                          |
+------+------------+                 +-----------+---------+
| ProactiveMonitor  |                 | Prometheus          |
| Engine            |                 | (port 9090)         |
| src/engine/       |                 +---------------------+
| proactive_engine  |                           |
|                   |                 +-----------+---------+
|  LogPreprocessor  |                 | Grafana             |
|  BehaviorModel    |                 | (port 3000)         |
|  AnomalyDetector  |                 +---------------------+
|  SeverityClassif. |
+------+------------+
       |
+------+------------+
| AlertManager      |
| src/alerts/       |
| manager.py        |
| (ring buffer)     |
+-------------------+
```

### Component Interactions

**FastAPI service** (`src/api/app.py`). The UI's sole backend. The UI calls existing REST endpoints for health checks, alert retrieval, and RAG queries. Three new endpoints — `/ws/alerts`, `/pipeline/status`, and `/score/history` — must be added to `src/api/routes.py` to support the monitoring panels. All UI requests use the same API key authentication that governs all other clients. The UI should pass the `X-API-Key` header on every request that is not on the public endpoint list (`/health`, `/metrics`, `/`, `/query`).

**ProactiveMonitorEngine** (`src/engine/proactive_engine.py`). After Phase 7 of the refactor, this class replaces the current `Pipeline` container as the authoritative runtime coordinator. It exposes a `metrics_snapshot()` method that returns the load state, mode, and threshold values for each of the six pipeline components. The `/pipeline/status` endpoint delegates directly to this method. The UI displays this snapshot as the Pipeline Component Status panel.

**AlertManager** (`src/alerts/manager.py`). Manages the alert lifecycle: deduplication, cooldown suppression, and the `_alert_buffer` ring buffer (capacity governed by `ALERT_BUFFER_SIZE`, default 200). The `GET /alerts` endpoint exposes this buffer as a JSON list. The `/ws/alerts` WebSocket endpoint provides real-time push of new alerts as they are appended to this buffer. The UI Alert Feed consumes both endpoints: the REST endpoint for initial load and historical context, and the WebSocket for live push updates.

**Prometheus** (`prometheus/prometheus.yml`, port 9090). Prometheus scrapes `GET /metrics` on the FastAPI service every 15 seconds. Key counters exposed: `ingest_events_total`, `windows_scored_total`, `alerts_total` (labeled by severity), `ingest_latency_seconds`, `scoring_latency_seconds`. After Phase 7, new metrics will be added: `reconstruction_error_histogram`, `severity_info_total`, `severity_warning_total`, `severity_critical_total`. The UI can read these metrics by polling `GET /metrics` directly and parsing the Prometheus text format, or by delegating metric visualization to the embedded Grafana dashboard via an iframe.

**Grafana** (port 3000). The existing Stage 08 dashboard (`grafana/dashboards/stage08_api_observability.json`) displays five infrastructure panels: events rate, windows rate, alerts by severity (stacked), ingest latency p95, and scoring latency p95. The UI should embed or link to this dashboard for infrastructure-level metrics rather than duplicating those visualizations. The UI's own score timeline chart is a different signal: it shows per-window reconstruction error over time, which is not a Prometheus counter and is not present in the Grafana dashboard.

**RAG investigation layer** (`src/api/ui.py`, `POST /query`). Currently implemented as a keyword-match stub against an eight-document hardcoded knowledge base. After Phase 7, the `/query` endpoint must be upgraded to query over three live data sources: the alert ring buffer, the score history ring buffer, and the log window evidence attached to each alert. The RAG layer is strictly an explanation interface. It is not involved in anomaly detection, alert routing, or model scoring. It is activated only when the operator explicitly selects an alert and submits a natural-language question.

---

## 3. UI Architecture

### Data Flow

```
Raw Log Line
    |
    v  [src/parsing/parsers.py]
LogEvent
    |
    v  [src/preprocessing/log_preprocessor.py]
Float vector [vec_dim=100]
    |
    v  [src/modeling/behavior_model.py]
Context Vector [hidden_dim]
    |
    v  [src/modeling/anomaly_detector.py]
reconstruction_error (float) + latent_vector
    |
    v  [src/modeling/severity_classifier.py]
Severity: Info | Warning | Critical
    |
    v  [src/engine/proactive_engine.py]
    |         |                   |
    v         v                   v
RiskResult  AlertManager     MetricsRegistry
    |         |    |              |
    |         v    v              v
    |      Alert  Ring          Prometheus
    |      fired  buffer        /metrics
    |             |
    v             v
  POST /ingest  GET /alerts
  response      GET /ws/alerts (push)
                GET /score/history
                GET /pipeline/status
                     |
                     v
              +------+----------+
              |   FastAPI API   |
              |   (port 8000)   |
              +------+----------+
                     |
              HTTP / WebSocket
                     |
              +------+----------+
              |  UI Dashboard   |
              |  (Streamlit /   |
              |   HTML)         |
              +------+----------+
                     |
              (alert selected)
                     |
              POST /query  <--- RAG Investigation
              GET /alerts/{id}     Panel
```

### Architectural Constraints

The UI enforces a strict read-only contract with the API. It never calls `POST /ingest` directly. Event ingestion is the responsibility of the log producer (the application sending log events to the API). The UI observes the results of that ingestion through the alert and score history endpoints.

The UI does not embed any model inference logic. It does not load model artifacts from `models/`. All intelligence is delivered through the API response payloads.

The UI polling and WebSocket connections must respect the `ALERT_COOLDOWN_SECONDS` configuration. The UI should not display more than one alert per stream key within the cooldown window because the `AlertManager` suppresses those duplicates before they reach the buffer.

---

## 4. UI Screens and Views

The UI is organized as five panels. In the Streamlit implementation, these panels occupy a two-column layout with a sidebar. In the HTML template implementation, they are organized as stacked sections with tab navigation.

---

### Panel 1 — System Status

**Purpose.** Provide an at-a-glance summary of system health and pipeline readiness. This panel loads first and remains visible in all UI states.

**Data source.** `GET /health`

**Content.**

The panel displays the three fields returned by the `HealthResponse` schema:

- `status`: rendered as a colored indicator badge (`healthy` = green, `degraded` = amber, `unhealthy` = red, `unknown` = grey).
- `uptime_seconds`: rendered as a human-readable uptime string (e.g., "4h 12m").
- `components`: a table listing each registered component (pipeline, alert_manager, inference_engine), its individual status, and any detail message. After Phase 7, `ProactiveMonitorEngine` will register each of the six AI pipeline components as individual health sub-checks.

**Refresh behavior.** Polled every 30 seconds. The status badge updates without a full page reload.

**Pre-refactor availability.** Fully available now. `GET /health` is implemented and returns a valid `HealthResponse`. No API changes required.

---

### Panel 2 — Live Alert Feed

**Purpose.** Display the current alert ring buffer and surface new alerts in real time as they are pushed by the WebSocket connection.

**Data sources.**
- `GET /alerts` — initial load of the ring buffer (up to `ALERT_BUFFER_SIZE` alerts, default 200).
- `GET /ws/alerts` — WebSocket for live push of new alerts after page load.

**Content.**

A sortable, filterable table with one row per alert. Columns derived from `AlertSchema`:

| Column | Source Field | Notes |
|---|---|---|
| Time | `timestamp` | Formatted as local datetime |
| Service | `service` | Stream key (e.g., `hdfs`, `bgl`) |
| Severity | `severity` | Badge: Critical (red), High (orange), Medium (amber), Info (grey) |
| Score | `score` | Decimal, two places |
| Threshold | `threshold` | Decimal, two places |
| Score/Threshold Ratio | computed | `score / threshold`, rendered as a bar |
| Model | `model_name` | e.g., `autoencoder`, `baseline`, `ensemble` |
| Alert ID | `alert_id` | Truncated UUID; click to open detail |

New alerts pushed via WebSocket are prepended to the table with a brief highlight animation to draw operator attention.

Filter controls: severity level (multi-select), service name (multi-select), time range (last 15m / 1h / 6h / all).

**Interaction.** Clicking any row sets that alert as the selected alert context and activates the RAG Investigation Panel (Panel 5).

**Pre-refactor availability.** `GET /alerts` is fully implemented. `GET /ws/alerts` must be added (Phase 8, Task 1 of the implementation plan). The table can be built now using the REST endpoint with periodic polling as a placeholder until the WebSocket is available.

---

### Panel 3 — Score Timeline

**Purpose.** Show the reconstruction error (anomaly score) over time as a continuous line chart with anomaly event annotations. This panel is the primary diagnostic signal for operators investigating behavioral drift before an alert fires.

**Data source.** `GET /score/history`

**Content.**

A time-series line chart where:
- The X axis is the window timestamp (`RiskResultSchema.timestamp`).
- The Y axis is the risk score (`RiskResultSchema.risk_score`). After Phase 7 refactor, this field carries the reconstruction error from `AnomalyDetector`.
- A horizontal reference line is drawn at the anomaly threshold (`RiskResultSchema.threshold`).
- Points where `is_anomaly=True` are plotted with a distinct marker (e.g., red dot) to differentiate anomalous windows from normal windows.
- Stream key (service) can be selected from a dropdown to filter the chart to a single service's windows.

Below the chart, a secondary bar chart shows severity distribution: count of Info, Warning, and Critical alerts in the same time window, sourced from the filtered alert buffer.

**Refresh behavior.** The score history endpoint is polled every 10 seconds to append new windows. Chart renders with smooth append animation.

**Pre-refactor availability.** `GET /score/history` does not exist yet. It must be added as a new endpoint backed by a ring buffer of `RiskResult` objects maintained in `Pipeline` (or `ProactiveMonitorEngine` after Phase 7). Implementation is a straightforward extension of the existing `_alert_buffer` pattern in `src/api/pipeline.py`: add a `_score_buffer: deque` with configurable capacity (suggested env var: `SCORE_HISTORY_SIZE`, default 500).

---

### Panel 4 — Pipeline Component Status

**Purpose.** Show the operational state of each component in the six-stage OOP AI pipeline. This panel allows operators to verify which model artifacts are loaded, which inference mode is active, and what the current threshold values are for each model.

**Data source.** `GET /pipeline/status`

**Content.**

A component status table with one row per pipeline stage:

| Stage | Class | Status | Model File | Threshold / Config |
|---|---|---|---|---|
| 1. NLP Embedding | `LogPreprocessor` | Loaded / Not loaded | `models/word2vec.model` | vec_dim=100 |
| 2. Sequence Data | `LogDataset` | Active / Standby | N/A (runtime) | window=50, stride=10 |
| 3. Behavior Model | `SystemBehaviorModel` | Loaded / Not loaded | `models/behavior_model.pt` | hidden_dim=128 |
| 4. Anomaly Detector | `AnomalyDetector` | Loaded / Not loaded | `models/anomaly_detector.pt` | threshold (from `artifacts/threshold_autoencoder.json`) |
| 5. Severity Classifier | `SeverityClassifier` | Loaded / Not loaded | `models/severity_classifier.pt` | 3 classes |
| 6. Engine | `ProactiveMonitorEngine` | Active / Degraded | N/A | mode, uptime |

Below the component table, a configuration summary block shows the active environment settings relevant to the pipeline: `MODEL_MODE`, `WINDOW_SIZE`, `STRIDE`, `ALERT_COOLDOWN_SECONDS`, `DEMO_MODE`.

**Pre-refactor availability.** `GET /pipeline/status` does not exist yet. During Phases 1 through 6 of the refactor (before `ProactiveMonitorEngine` is built), this endpoint can return a simplified status derived from the existing `Pipeline` class: the `InferenceEngine` mode and whether `load_artifacts()` completed successfully. The full per-component breakdown becomes available in Phase 7 when `ProactiveMonitorEngine.metrics_snapshot()` is implemented.

---

### Panel 5 — RAG Investigation Panel

**Purpose.** Enable operators to ask natural-language questions about a selected alert. The panel surfaces evidence from the alert itself, the score timeline surrounding the alert timestamp, and historical alert context for the same service. It is activated exclusively by selecting an alert in Panel 2.

**Data sources.**
- `GET /alerts/{alert_id}` — detailed alert data including full `evidence_window`.
- `POST /query` — RAG backend; question is sent with the selected alert's context as grounding metadata.
- `GET /score/history` — score timeline data anchored around the alert timestamp.

**Content.**

The panel has three sections:

**Alert Evidence Summary.** Displays the selected alert's full detail: alert ID, service, severity, score, threshold, model name, timestamp, and the complete `evidence_window` dictionary (the token sequence or log window that triggered the alert).

**Score Context Window.** A mini chart showing reconstruction error in the 60-second window before and after the alert timestamp, sourced from `GET /score/history` filtered by timestamp range and service. This allows the operator to see whether the anomaly was a spike or the end of a sustained drift.

**AI Investigation Interface.** A text input field where the operator submits a natural-language question. The question and the selected alert's metadata are sent to `POST /query`. The response renders as:
- A short plain-language answer paragraph.
- A list of evidence sources with IDs, relevance scores, and snippets.

Example question types this panel is designed to handle:
- "Why did this alert fire?"
- "Has this service triggered critical alerts before?"
- "What was the reconstruction error trend before this alert?"
- "What model scored this window and what was the threshold?"

**Interaction state.** When no alert is selected, this panel renders a placeholder message: "Select an alert from the Live Alert Feed to begin investigation." The panel never initiates queries autonomously — all RAG calls are user-initiated by submitting the question form.

**Pre-refactor availability.** The panel can be built immediately using the existing `POST /query` stub and `GET /alerts` response data. The investigation quality improves in phases as the RAG backend is upgraded (see Section 6). `GET /alerts/{alert_id}` does not exist yet and must be added to `src/api/routes.py`.

---

## 5. Required API Endpoints

The table below maps each UI panel to its backend data sources and specifies whether each endpoint is currently implemented.

| Endpoint | Method | Consumer Panel | Status |
|---|---|---|---|
| `/health` | GET | System Status | Implemented |
| `/alerts` | GET | Live Alert Feed, RAG Panel | Implemented |
| `/metrics` | GET | Infrastructure link / Grafana bridge | Implemented |
| `/query` | POST | RAG Investigation Panel | Stub only — must be upgraded |
| `/ws/alerts` | WebSocket | Live Alert Feed (live push) | Not implemented |
| `/pipeline/status` | GET | Pipeline Component Status | Not implemented |
| `/score/history` | GET | Score Timeline, RAG Panel | Not implemented |
| `/alerts/{alert_id}` | GET | RAG Panel (detail view) | Not implemented |

---

### `GET /health`

**Currently implemented.** Returns `HealthResponse` with `status`, `uptime_seconds`, and `components`. Consumed by Panel 1. No changes required for Phase 1 UI. In Phase 2, the `components` dict should include individual status entries for each of the six `ProactiveMonitorEngine` stages, added when Phase 7 of the ML refactor is complete.

**Response schema** (existing `src/api/schemas.py`):
```json
{
  "status": "healthy",
  "uptime_seconds": 3672.4,
  "components": {
    "pipeline": {"status": "healthy"},
    "alert_manager": {"status": "healthy"}
  }
}
```

---

### `GET /alerts`

**Currently implemented.** Returns `AlertListResponse` with `count` and a list of `AlertSchema` objects from the `Pipeline._alert_buffer` ring buffer. Consumed by Panel 2 (initial load) and Panel 5 (alert selection). No changes required.

**Response schema** (existing `src/api/schemas.py`):
```json
{
  "count": 3,
  "alerts": [
    {
      "alert_id": "a1b2c3d4-...",
      "severity": "critical",
      "service": "bgl",
      "score": 1.82,
      "timestamp": 1741296000.0,
      "evidence_window": {"tokens": [14, 7, 23], "length": 50},
      "model_name": "autoencoder",
      "threshold": 0.307,
      "meta": {}
    }
  ]
}
```

---

### `GET /ws/alerts`

**Not implemented.** Must be added to `src/api/routes.py`.

**Role.** Provides real-time push of new alerts to connected UI clients. When `Pipeline.process_event()` appends a new alert to `_alert_buffer`, all connected WebSocket clients receive the new alert as a JSON message matching the `AlertSchema` structure.

**Implementation note.** The `Pipeline` class has no push notification mechanism today. The recommended implementation is to maintain an `asyncio.Queue` per connected WebSocket client in `app.state`. When `process_event()` fires an alert, it calls a registered callback that enqueues the alert dict to all active client queues. The WebSocket handler consumes its queue and sends. This avoids polling and delivers alerts to the UI within one event loop tick of the alert firing.

**Authentication.** This endpoint should be added to `PUBLIC_ENDPOINTS` or accept the API key as a query parameter (`?api_key=...`) since browser WebSocket connections cannot set custom headers.

**Expected message format.** Identical to a single `AlertSchema` JSON object, newline-delimited.

---

### `GET /pipeline/status`

**Not implemented.** Must be added to `src/api/routes.py`, backed by `ProactiveMonitorEngine.metrics_snapshot()` after Phase 7.

**Role.** Returns the operational state of each pipeline component: which model artifacts are loaded, the active inference mode, current threshold values, and the pipeline uptime. Consumed by Panel 4.

**Interim implementation (Phases 1-6 of refactor).** Before `ProactiveMonitorEngine` exists, this endpoint can be backed by the existing `Pipeline` class and return a simplified subset: engine mode, whether `load_artifacts()` succeeded, `window_size`, `stride`, and `alert_cooldown_seconds` from settings.

**Proposed response schema** (new, to be defined in `src/api/schemas.py`):
```json
{
  "mode": "autoencoder",
  "uptime_seconds": 3672.4,
  "demo_mode": false,
  "window_size": 50,
  "stride": 10,
  "alert_cooldown_seconds": 60.0,
  "components": {
    "log_preprocessor": {
      "loaded": true,
      "artifact": "models/word2vec.model",
      "vec_dim": 100
    },
    "system_behavior_model": {
      "loaded": true,
      "artifact": "models/behavior_model.pt",
      "hidden_dim": 128
    },
    "anomaly_detector": {
      "loaded": true,
      "artifact": "models/anomaly_detector.pt",
      "threshold": 0.043
    },
    "severity_classifier": {
      "loaded": true,
      "artifact": "models/severity_classifier.pt",
      "classes": ["info", "warning", "critical"]
    }
  }
}
```

---

### `GET /score/history`

**Not implemented.** Must be added to `src/api/routes.py`.

**Role.** Returns the last N scored windows as a time-ordered list of `RiskResultSchema` objects. Consumed by Panel 3 (full chart) and Panel 5 (mini context window around alert timestamp).

**Query parameters.**
- `n` (int, default 500): maximum number of windows to return.
- `service` (str, optional): filter by stream key / service name.
- `since` (float, optional): Unix timestamp; return only windows after this time.

**Implementation note.** Add a `_score_buffer: deque` to `Pipeline` (or `ProactiveMonitorEngine`) in `src/api/pipeline.py`, analogous to the existing `_alert_buffer`. Every call to `process_event()` that returns a non-None `risk_result` appends that result to this buffer. Buffer capacity is controlled by a new env var `SCORE_HISTORY_SIZE` (default 500). The endpoint filters and returns the buffer contents.

**Proposed response schema** (new, to be defined in `src/api/schemas.py`):
```json
{
  "count": 120,
  "windows": [
    {
      "stream_key": "bgl",
      "timestamp": 1741296000.0,
      "model": "autoencoder",
      "risk_score": 0.041,
      "is_anomaly": false,
      "threshold": 0.043,
      "evidence_window": {"length": 50}
    }
  ]
}
```

---

### `POST /query`

**Stub implemented** (`src/api/ui.py`). Currently performs keyword matching against eight hardcoded knowledge base documents. Returns `QueryResponse` with `answer` (string) and `sources` (list of `SourceDoc`). Must be upgraded in Phase 3 of UI development.

**Role in the UI.** Receives natural-language questions from Panel 5, grounded by the selected alert's context. Returns a plain-language answer and supporting evidence snippets.

**Required upgrade path.** The stub must be replaced with a backend that queries three live data sources: the alert ring buffer, the score history ring buffer, and the log window evidence fields from `AlertSchema.evidence_window`. See Section 6 for the full RAG integration specification.

**Authentication.** `POST /query` is currently on the `PUBLIC_ENDPOINTS` list (`/health,/metrics,/,/query`). This should remain unchanged.

---

### `GET /alerts/{alert_id}`

**Not implemented.** Must be added to `src/api/routes.py`.

**Role.** Returns the full detail of a single alert by its `alert_id`. Consumed by Panel 5 to load the alert evidence before the operator submits a RAG question.

**Implementation note.** The `Pipeline._alert_buffer` stores alert dicts keyed sequentially. To support lookup by ID, the buffer must be searchable by `alert_id`. The simplest implementation is a linear scan of the ring buffer deque (O(n), n <= 200 — acceptable). An alternative is to maintain a secondary `dict[str, dict]` mapping `alert_id` to the alert dict alongside the ring buffer.

**Proposed response schema.** A single `AlertSchema` object (same as elements of `AlertListResponse.alerts`).

---

## 6. RAG Integration

### Design Principle

RAG is an explanation layer, not a detection layer. It is triggered exclusively by operator action — selecting an alert and submitting a question. It plays no role in the anomaly detection pipeline. The `AnomalyDetector`, `SeverityClassifier`, and `AlertManager` complete their work before RAG is ever involved. RAG reads from their outputs; it does not influence them.

### Trigger Flow

```
Operator selects alert in Panel 2 (Live Alert Feed)
    |
    v
GET /alerts/{alert_id}
    -> Load full alert evidence into Panel 5
    |
    v
GET /score/history?service={service}&since={alert_time - 60s}
    -> Load score context window into Panel 5 mini-chart
    |
    v
Operator types question and submits
    |
    v
POST /query
    body: {
        "question": "Why did this alert fire?",
        "context": {
            "alert_id": "a1b2c3d4-...",
            "service": "bgl",
            "severity": "critical",
            "score": 1.82,
            "threshold": 0.307,
            "evidence_window": {...}
        }
    }
    |
    v
RAG backend queries three sources:
    1. Alert ring buffer  -> recent alerts for same service
    2. Score history      -> reconstruction error trend around alert time
    3. Evidence window    -> token sequence / log window from the alert
    |
    v
Returns: { answer: "...", sources: [...] }
    |
    v
Rendered in Panel 5 investigation interface
```

### Data Sources Queried by RAG

**Alert history** (primary source). The alert ring buffer (`Pipeline._alert_buffer`, capacity 200) contains all recently fired alerts as serialized `AlertSchema` dicts. The RAG backend scans this buffer for alerts matching the same `service` as the selected alert, retrieving their scores, severities, timestamps, and model names. This gives the answer grounding in the pattern of alerts for that service (e.g., "This service has fired 4 critical alerts in the past 2 hours, all with scores between 1.6 and 2.1 at the `autoencoder` threshold").

**Score history** (secondary source). The score history ring buffer contains the last N `RiskResult` objects. Filtering by `service` and the time range surrounding the alert timestamp reveals whether the anomaly was a sharp spike or a sustained high-reconstruction-error trend. This context is essential for distinguishing transient noise from systematic behavioral drift.

**Log window evidence** (tertiary source). Each `AlertSchema` carries an `evidence_window` dict containing the raw data that triggered the alert: the token sequence (pre-refactor) or the semantic embedding window (post-refactor). The RAG backend can surface the most anomalous tokens or the highest-deviation embedding dimensions from this evidence. After the full refactor, the `AnomalyDetector` latent vector and per-dimension reconstruction errors can be included here to give the operator a direct view of which log sequence features drove the reconstruction failure.

### RAG Backend Implementation

The current stub in `src/api/ui.py` uses hardcoded knowledge base documents and keyword matching. The upgrade required for Phase 3 does not require a vector database or an external LLM. The following implementation is sufficient for the project scope:

1. **Evidence assembly.** When `POST /query` receives a request with a `context` block containing an `alert_id`, the handler fetches the matching alert from the buffer, retrieves score history for the alert's service and timestamp window, and assembles a structured evidence dictionary.

2. **Keyword-augmented retrieval.** The question tokens are matched against the assembled evidence using the existing `_top_sources()` ranking pattern, extended to score against the live evidence rather than the static knowledge base. Terms like "reconstruction", "score", "service", "critical", "trend" are matched against the evidence fields.

3. **Template-based answer generation.** The answer is composed from a set of evidence-driven answer templates. For example: if `score / threshold > 1.5`, the template is "The alert was classified as Critical because the reconstruction error ({score:.3f}) exceeded the anomaly threshold ({threshold:.3f}) by a factor of {ratio:.1f}x." This is deterministic, transparent, and requires no external LLM dependency.

4. **Future enhancement path.** After the system is stable, a local language model (via `ollama` or `llama.cpp`) can be integrated as the answer generation layer, replacing the template system. The `POST /query` interface contract does not change, only the backend implementation of `_best_answer()` in `src/api/ui.py`.

### RAG Isolation Guarantee

The RAG backend must never write to the alert buffer, the score buffer, the `AlertManager`, or any pipeline component. It is a read-only consumer of already-committed data. All query handlers in `ui.py` must be implemented as pure functions with no side effects on the application state.

---

## 7. UI Technology

### Option A — Extend Existing HTML Template (`templates/index.html`)

**Current state.** The existing `templates/index.html` is a single-file vanilla JavaScript application with a three-tab layout (Ingest / Alerts / RAG Ask), a dark theme, inline CSS, and no external JavaScript dependencies. It is served by `GET /` via `src/api/ui.py` as a raw `HTMLResponse`. It is already included in the Docker image.

**Feasibility for Option 2.** The existing template is structurally adequate for Panel 1 (System Status) and Panel 2 (Live Alert Feed). Adding the Score Timeline chart (Panel 3) would require either a native SVG line chart implementation or embedding a CDN-hosted charting library (Chart.js or Plotly.js via `<script src="...">` from a CDN). The Pipeline Component Status panel (Panel 4) is straightforward table markup. The RAG Investigation Panel (Panel 5) requires the most new markup but is achievable within a single HTML file.

**Limitations.** The WebSocket client must be implemented in vanilla JavaScript. Score history polling must be implemented manually. Chart animation and reactivity require significant JavaScript complexity for a single-file approach. The resulting file becomes difficult to maintain beyond ~1,200 lines.

**Verdict.** Viable for Phase 1 (monitoring panels only). Becomes a maintenance liability in Phases 2 and 3 as chart complexity and panel interaction state grows. Acceptable if the developer prefers to avoid adding new Python dependencies.

---

### Option B — Streamlit (`src/ui/dashboard.py`)

**Overview.** Streamlit is a Python framework for building data applications. It renders UI components from Python function calls, handles state management, and natively supports `httpx`/`requests` for API calls, `plotly`/`altair` for charts, and `websockets` for real-time data.

**Advantages for this project.**
- Python-native: the developer writes the same language used for all backend and ML code. No context switching to JavaScript.
- Chart support: `st.line_chart()`, `st.plotly_chart()`, and `st.altair_chart()` cover all visualization needs for Panels 3 and 5 without CDN dependencies.
- State management: `st.session_state` handles the selected alert context across panels cleanly.
- Separation of concerns: Streamlit runs as a separate process from the FastAPI server. It calls the FastAPI API over HTTP, respecting the same API contract that all other clients use. It does not import any FastAPI application code directly.
- Already in the implementation plan: Phase 8, Task 6 of `IMPLEMENTATION_ACTION_PLAN.md` specifies "create `src/ui/dashboard.py` as a Streamlit app that calls the FastAPI endpoints."
- Development dependency only: `streamlit` belongs in `requirements-dev.txt`, not production `requirements.txt`. The Streamlit dashboard is not part of the Docker image.
- Live refresh: `st.rerun()` with a configurable interval (or `asyncio` with `websockets`) provides the live alert feed without building a manual polling loop.

**Limitations.** Streamlit applies a fixed page layout model and a distinctive visual style. It is not suitable for highly custom layouts, service maps, or complex drag-and-drop interfaces. For Option 2 (Observability + Investigation Center), these limitations are not relevant — the required panels map cleanly to Streamlit's component model.

**Verdict.** Streamlit is the recommended technology for this project. It aligns with Phase 8 of the implementation plan, requires no new build tooling, and covers all five panel types without leaving the Python ecosystem.

---

### Option C — React

**Overview.** A JavaScript component framework requiring a build chain (`npm`, `webpack` or `vite`, `package.json`, `node_modules`).

**Advantages.** Full layout flexibility. Real-time WebSocket handling is native in JavaScript. Third-party component libraries (Recharts, D3, Cytoscape.js) cover any visualization need.

**Disadvantages for this project.** The project currently has zero frontend build infrastructure. Introducing React requires creating and maintaining a separate build pipeline (`package.json`, bundler configuration, deployment artifacts), a separate development server, and a separate test suite. The development overhead is disproportionate to the UI requirements of Option 2. React is the correct choice for Option 3 (AIOps Command Center) with its service maps and incident management, but it is overengineered for the monitoring and investigation panels defined here.

**Verdict.** Not recommended for this project at this stage. Reconsider if the UI requirements escalate to Option 3 scope (service topology maps, incident lifecycle views, heatmaps).

---

### Recommendation Summary

| Criterion | HTML Template | Streamlit | React |
|---|---|---|---|
| Python-only development | No | Yes | No |
| Chart library included | No (CDN required) | Yes (native) | No (library required) |
| WebSocket support | Manual JS | Via `websockets` lib | Native |
| State management | Manual JS | `st.session_state` | React state/hooks |
| Build toolchain required | No | No | Yes |
| Docker deployment | Bundled in image | Separate process | Separate build + serve |
| Aligned with Phase 8 plan | Partially | Fully | No |
| Maintenance complexity | Medium | Low | High |

**Chosen technology: Streamlit.** Location: `src/ui/dashboard.py`. Added to `requirements-dev.txt`. Not included in the production Docker image. Deployed locally alongside the Docker Compose stack by running `streamlit run src/ui/dashboard.py` after the stack is up.

---

## 8. Development Phases

UI development is staged to align with the ML refactor phases defined in `IMPLEMENTATION_ACTION_PLAN.md`. Each UI phase builds on a corresponding refactor milestone.

---

### Phase 1 — Monitoring UI

**Refactor dependency.** Can begin immediately. All required endpoints (`GET /health`, `GET /alerts`) are already implemented. Phase 1 does not require any ML refactor progress.

**Deliverables.**
1. `src/ui/dashboard.py` — Streamlit app skeleton with sidebar navigation and page routing.
2. Panel 1 (System Status): health status badge, uptime display, components table from `GET /health`.
3. Panel 2 (Live Alert Feed): alert table from `GET /alerts` with severity badges and polling every 15 seconds. Alert selection state stored in `st.session_state`.
4. Panel 4 (Pipeline Component Status) — interim version: current engine mode, window/stride settings from a polled `GET /pipeline/status` interim endpoint. The interim endpoint is backed by the existing `Pipeline` settings, not `ProactiveMonitorEngine`.
5. Add interim `GET /pipeline/status` endpoint to `src/api/routes.py` returning `Pipeline` settings.
6. Add `streamlit` and `plotly` to `requirements-dev.txt`.
7. `src/ui/README.md` — startup instructions (how to run Streamlit alongside the Docker Compose stack).

**Completion criterion.** Streamlit dashboard launches, connects to the running FastAPI service, displays current health status and alert table. All 233 existing tests continue passing.

---

### Phase 2 — Investigation UI

**Refactor dependency.** Requires Phase 4 of the ML refactor (LSTM training complete) for meaningful score history data. The UI panel can be scaffolded before that, but the chart will show minimal data until reconstruction errors begin flowing.

**Deliverables.**
1. `GET /score/history` endpoint added to `src/api/routes.py`, backed by a new `_score_buffer` in `Pipeline`.
2. `GET /alerts/{alert_id}` endpoint added to `src/api/routes.py`.
3. Panel 3 (Score Timeline): Plotly line chart with threshold reference line and anomaly markers. Service filter dropdown. 10-second polling refresh.
4. Panel 2 upgraded: clicking an alert row sets `st.session_state.selected_alert` and triggers Panel 5 to load alert detail.
5. Panel 5 (RAG Investigation Panel) — stub version: displays selected alert's full `evidence_window` and score context mini-chart. RAG question form present but backed by the existing keyword-match `/query` stub.
6. `GET /ws/alerts` WebSocket endpoint added to `src/api/routes.py`. Panel 2 upgraded to consume the WebSocket for live push using the `websockets` Python library in a background thread.
7. Panel 4 upgraded to full version when Phase 7 (ProactiveMonitorEngine) is complete: per-component loaded/not-loaded status from the upgraded `GET /pipeline/status` response.

**Completion criterion.** Score timeline displays reconstruction error over time. Alert selection activates Panel 5 with full evidence detail. New alerts appear in Panel 2 within one second via WebSocket.

---

### Phase 3 — RAG Investigation Layer

**Refactor dependency.** Requires Phase 7 (ProactiveMonitorEngine complete) and meaningful alert history data — at minimum 50 fired alerts in the ring buffer to provide sufficient RAG retrieval context.

**Deliverables.**
1. `POST /query` backend upgraded in `src/api/ui.py`: replace static knowledge base with live query over alert buffer, score history buffer, and evidence window data.
2. `POST /query` request schema extended to accept a `context` block containing `alert_id`, `service`, and `evidence_window`.
3. Template-based answer generation: evidence-driven answer templates covering the most common operator questions (score/threshold ratio explanation, service history, trend description).
4. Panel 5 fully operational: answer paragraph rendered with citation list, score context chart updates on alert selection, evidence window fields rendered in expandable detail section.
5. Update `POST /query` to include `alert_id` in the RAG context when the request is submitted from Panel 5. The `context` field is optional; existing uses of `/query` without alert context continue to work (backward-compatible).
6. Integration test: `tests/integration/test_smoke_api.py` extended with a test that selects an alert ID from `GET /alerts`, calls `GET /alerts/{alert_id}`, and calls `POST /query` with the alert context, asserting a non-empty answer.

**Completion criterion.** Selecting an alert in Panel 2 and submitting "Why did this alert fire?" to Panel 5 returns a grounded, evidence-based answer citing the alert's score, threshold, and service history. Answer quality is measurably better than the current static stub for questions about scores, thresholds, and service patterns.

---

## 9. Risks and Limitations

### Risk 1 — ML Pipeline Dependency (Medium)

The Score Timeline (Panel 3) and the RAG investigation quality (Panel 5) depend directly on the quality and availability of ML pipeline outputs. During Phases 1 through 5 of the ML refactor, `risk_score` values in `score/history` will be produced by the existing `IsolationForest` or `Transformer` models, not the new `AnomalyDetector`. These scores have a narrow distribution (0.297 to 0.443 for the baseline model) and limited interpretability. The score timeline will be functional but will not show the reconstruction error semantics the OOP refactor is designed to produce.

Mitigation: Phase 1 and Phase 2 UI development proceed with current model outputs. The score timeline chart and RAG investigation panel improve automatically once Phase 5 (`AnomalyDetector`) and Phase 6 (`SeverityClassifier`) are complete. No UI code changes are required for this upgrade — only the backend data changes.

### Risk 2 — RAG Data Availability (Medium)

The RAG investigation panel requires a minimum number of fired alerts in the ring buffer to provide meaningful retrieval context. In a fresh deployment with `DEMO_MODE=false` and no incoming log traffic, the alert buffer is empty and the RAG backend has no evidence to query. The investigation panel will return default-template answers that reference only the selected alert's own fields.

Mitigation: The existing demo warmup mechanism (`DEMO_WARMUP_ENABLED=true`, `DEMO_WARMUP_EVENTS=75`) can be activated during development and demonstration to pre-populate the alert buffer. In production, the buffer fills naturally as the log stream flows. Document the minimum recommended buffer fill (50 alerts) before the RAG panel is expected to return meaningful multi-alert context.

### Risk 3 — Real-Time Alert Streaming (Low)

The `GET /ws/alerts` WebSocket endpoint requires an async notification mechanism inside `Pipeline.process_event()`. The current `Pipeline` is synchronous: it appends to `_alert_buffer` as a side effect but does not notify any external subscribers. Adding async notification requires adding an `asyncio.Queue` per client and ensuring that `process_event()` — which is called from an `async` FastAPI route handler — can safely enqueue without blocking.

Mitigation: Use `asyncio.Queue` with `put_nowait()` (non-blocking). Maintain the list of active client queues in `app.state`. If no WebSocket clients are connected, `process_event()` skips the notification entirely with no overhead. The existing REST polling of `GET /alerts` serves as the fallback if the WebSocket connection is lost.

### Risk 4 — Console Encoding (Low)

As documented in `MEMORY.md`, the project runs on Windows with `stdout` encoding `cp1255`. Print statements and log messages in the Streamlit dashboard must use only ASCII characters. Non-ASCII symbols (arrows, em-dashes, degree signs) in Streamlit widget labels or log output will render incorrectly on this platform.

Mitigation: Enforce ASCII-only strings in all `print()` calls and `logger.*()` calls within `src/ui/dashboard.py`. Streamlit's web-rendered HTML widgets support Unicode normally — this constraint applies only to terminal output.

### Risk 5 — Streamlit Polling vs. WebSocket Concurrency (Low)

Streamlit's execution model reruns the entire script on each user interaction or `st.rerun()` call. Running a WebSocket listener in the background and updating `st.session_state` from it requires threading or `asyncio` bridge code. A naive implementation that opens a new WebSocket connection on every script rerun will exhaust connections quickly.

Mitigation: Use `st.cache_resource` to initialize a single persistent WebSocket connection or a background polling thread that is shared across reruns. The `_alert_buffer` REST endpoint serves as the primary alert source; the WebSocket is an enhancement for push latency, not a hard requirement. Phase 2 can deliver the WebSocket integration after basic polling is confirmed stable.

---

## 10. Implementation Recommendations

### Starting Point

Begin with `src/ui/dashboard.py` as a standalone Python script. The file must import only `streamlit`, `httpx`, `plotly.express`, and standard library modules. It must not import any module from `src/`. All data access is through HTTP calls to the running FastAPI service.

```
src/
  ui/
    __init__.py
    dashboard.py     # Main Streamlit application
    api_client.py    # Thin wrapper around httpx for all API calls
    components/
      __init__.py
      status.py      # Panel 1: System Status renderer
      alert_feed.py  # Panel 2: Live Alert Feed renderer
      timeline.py    # Panel 3: Score Timeline chart
      pipeline.py    # Panel 4: Pipeline Component Status renderer
      rag.py         # Panel 5: RAG Investigation Panel renderer
    README.md        # How to run
```

Splitting panel rendering into separate component files in `src/ui/components/` prevents `dashboard.py` from becoming a monolith and allows independent testing of each panel renderer.

### API Client Layer

Create `src/ui/api_client.py` as a typed wrapper around `httpx`. All HTTP calls from the UI go through this client. This isolates URL construction, authentication header injection, and error handling in one place. When the API base URL or API key changes (e.g., different deployment environment), only `api_client.py` needs updating.

```python
# src/ui/api_client.py (structure only)
import httpx

class APIClient:
    def __init__(self, base_url: str, api_key: str) -> None: ...
    def get_health(self) -> dict: ...
    def get_alerts(self) -> list[dict]: ...
    def get_alert(self, alert_id: str) -> dict: ...
    def get_score_history(self, service: str | None, n: int) -> list[dict]: ...
    def get_pipeline_status(self) -> dict: ...
    def post_query(self, question: str, context: dict | None) -> dict: ...
```

### Configuration

The Streamlit dashboard requires two configuration values: the FastAPI base URL and the API key. These must be configurable via environment variables so the dashboard can connect to any deployment (local Docker, staging, production) without code changes.

```bash
export UI_API_BASE_URL=http://localhost:8000
export UI_API_KEY=your_api_key_here
streamlit run src/ui/dashboard.py
```

If `UI_API_KEY` is not set, the client omits the `X-API-Key` header and relies on `DISABLE_AUTH=true` in the API deployment (acceptable for local development only).

### New Endpoint Implementation Order

Add the four missing endpoints to `src/api/routes.py` in this order, as each unblocks a Phase of UI development:

1. **`GET /pipeline/status` (interim)** — trivial; returns `Pipeline` settings. Unblocks Phase 1, Panel 4.
2. **`GET /score/history`** — requires `_score_buffer` addition to `Pipeline`. Unblocks Phase 2, Panel 3.
3. **`GET /alerts/{alert_id}`** — linear scan of `_alert_buffer`. Unblocks Phase 2, Panel 5.
4. **`GET /ws/alerts`** — requires async notification mechanism. Unblocks Phase 2, Panel 2 live push.

Each endpoint must have a corresponding unit test added to `tests/unit/` and an integration smoke test in `tests/integration/test_smoke_api.py`. All new tests must pass under `pytest -m "not slow"`.

### Keeping Existing Tests Green

No changes to existing route behavior are permitted. The four new endpoints are additive. The existing `POST /ingest`, `GET /alerts`, `GET /health`, `GET /metrics`, `GET /`, and `POST /query` endpoints must continue to pass all 233 existing tests throughout UI development. Schema additions (new response models for `pipeline_status` and `score_history`) must be defined in `src/api/schemas.py` without modifying existing schema classes.

### Grafana Integration

Do not attempt to replicate the Grafana infrastructure panels in the Streamlit dashboard. Instead, embed a direct link to the Grafana dashboard in the sidebar:

```python
st.sidebar.markdown(
    "[Open Grafana Dashboard](http://localhost:3000/d/stage08)"
)
```

Optionally, embed the Grafana dashboard using `st.components.v1.iframe()` in a dedicated "Infrastructure Metrics" tab. The Grafana admin credentials (`admin/admin` in local deployments) are documented in `docs/STAGE_35_STAGE_08_DOCKER_CICD_OBSERVABILITY.md`.

This division of responsibility keeps the Streamlit dashboard focused on AI pipeline observability (reconstruction errors, alert investigation, pipeline component state) while delegating infrastructure metrics (latency histograms, throughput counters, error rates) to the Grafana layer where they are already implemented and maintained.

---

## Part B: Repository Gap Analysis — UI Readiness Review
*Source: REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md — Section 8*

---

## 8. UI Readiness Review

### Current UI State

The project has a basic demo UI:
- `templates/index.html` — single-page HTML with three tabs (Ingest, Alerts, RAG Ask)
- `src/api/ui.py` — FastAPI router serving the HTML and a keyword-based RAG stub at `POST /query`
- Vanilla JavaScript; dark theme; no frontend build step required

This UI is functional for demonstration purposes but is not production-ready:
- The RAG stub (`_KB`, `_ANSWERS` dicts) is entirely static and hard-coded
- No real-time alert streaming (no WebSocket, no SSE)
- No chart/graph rendering of anomaly scores or trends
- No ability to upload log files
- No configuration panel

### What Kind of UI Architecture Would Fit Best

Given the Python-only requirement from the requirements document, the best UI approach is a **server-side Python framework** rather than a separate JavaScript frontend.

Three practical options:

**Option A: Streamlit (Recommended for Prototype)**
- Pure Python, no JavaScript required
- Built-in real-time components (st.metric, st.line_chart, st.dataframe)
- Easy integration with pandas DataFrames and Prometheus data
- Add a `streamlit run src/ui/dashboard.py` command

**Option B: Gradio (Recommended for ML Demo)**
- Pure Python, ML-focused widgets
- Excellent for showing model inputs/outputs interactively
- Can be embedded in the FastAPI app via `mount_gradio_app()`
- Best for demonstrating each pipeline stage individually

**Option C: FastAPI + Jinja2 Templates (Recommended for Production)**
- Already uses FastAPI; Jinja2 is a natural extension
- Server-side rendering with real data injected at render time
- Add WebSocket for live alert updates
- More effort but most professional and maintainable

### Lightest and Most Practical Python-Only Approach

For a project at this stage, **Streamlit** is the lightest path to a functional UI:

1. Install `streamlit` (single dependency)
2. Create `src/ui/dashboard.py`
3. Use `requests` to call the existing FastAPI `/ingest`, `/alerts`, `/health`, `/metrics` endpoints
4. Show live alert stream with `st.dataframe` auto-refresh
5. Show anomaly score chart with `st.line_chart`
6. Add log upload widget with `st.file_uploader`

This approach does not require modifying any existing code — it simply consumes the existing REST API.

**Important**: Do not build this until the underlying AI pipeline (Stages 1-5) is refactored first. A Streamlit UI on top of a misaligned pipeline will surface confusing outputs.
