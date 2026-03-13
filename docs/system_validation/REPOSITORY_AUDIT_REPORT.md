# Repository Audit Report
## Predictive Log Anomaly Engine

**Date:** 2026-03-09
**Status at audit:** Stages 1–8 complete, functionally production-ready
**Scope:** Analysis and documentation only — no runtime logic modified

---

## Table of Contents

1. [Repository Structure Analysis](#1-repository-structure-analysis)
2. [Configuration Consistency Report](#2-configuration-consistency-report)
3. [Metrics Consistency Report](#3-metrics-consistency-report)
4. [Duplicate File Detection](#4-duplicate-file-detection)
5. [Unused File Detection](#5-unused-file-detection)
6. [Documentation Coverage Analysis](#6-documentation-coverage-analysis)
7. [Naming Standardization Suggestions](#7-naming-standardization-suggestions)
8. [Recommended Final Repository Structure](#8-recommended-final-repository-structure)

---

## 1. Repository Structure Analysis

### Current Directory Tree

```
predictive-log-anomaly-engine/
├── .dockerignore               # Excludes data/, tests/, ai_workspace/, etc. from Docker image
├── .env.example                # Environment variable template (83 vars across all stages)
├── .gitignore                  # Ignores pycache, venv, data/, models/, reports/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions: lint + tests + security + docker smoke
├── Dockerfile                  # python:3.11-slim; uvicorn factory entrypoint; curl health check
├── docker-compose.yml          # api:8000, prometheus:9090, grafana:3000
├── main.py                     # Project entrypoint; delegates to scripts/stage_07_run_api.py
├── pyproject.toml              # pytest config: markers (slow, integration), testpaths
├── requirements.txt            # Production deps: fastapi, uvicorn, prometheus-client, sklearn, torch
├── requirements-dev.txt        # Dev deps: pytest, pytest-cov, ruff, flake8
├── README.md                   # High-level overview: architecture, demo walkthrough, tech stack
│
├── src/                        # All production Python source code (63 files, 17 modules)
│   ├── api/                    # FastAPI application factory, routes, schemas, settings
│   ├── runtime/                # Real-time inference: SequenceBuffer + InferenceEngine
│   ├── alerts/                 # AlertManager, N8N webhook client, ring buffer
│   ├── modeling/               # ML models: baseline (IsolationForest) + transformer (LSTM)
│   │   ├── baseline/           # BaselineAnomalyModel, BaselineFeatureExtractor, Calibrator
│   │   └── transformer/        # NextTokenTransformerModel, AnomalyScorer, Trainer
│   ├── observability/          # MetricsRegistry, MetricsMiddleware, configure_logging()
│   ├── security/               # AuthMiddleware (X-API-Key, public path bypass)
│   ├── health/                 # HealthChecker (healthy/degraded/unhealthy)
│   ├── parsing/                # Template miner (9-step regex), tokenizer, log parsers
│   ├── preprocessing/          # LogPreprocessor, GloVe embeddings
│   ├── sequencing/             # Session-based sequence builder, splitter
│   ├── data/                   # Synthetic log generator, patterns, scenario builder, LogEvent
│   ├── data_layer/             # Data access: Parquet/CSV loaders, ORM-like models
│   ├── dataset/                # LogDataset (iterable, train/val/test split)
│   ├── engine/                 # ProactiveEngine top-level orchestrator
│   ├── synthetic/              # Duplicate synthetic generator (see Section 4)
│   ├── core/contracts/         # Shared interfaces (placeholder)
│   └── app/                    # Empty placeholder module
│
├── tests/                      # 29 test files, 233 collected tests
│   ├── test_pipeline_smoke.py  # Fast smoke: MockPipeline + TestClient (18 tests)
│   ├── test_stage_06_*.py      # Alert policy, dedup, N8N outbox tests (3 files)
│   ├── test_stage_07_*.py      # Auth, ingest integration, metrics tests (3 files)
│   ├── helpers_stage_07.py     # MockPipeline helper
│   ├── integration/            # API integration smoke tests (test_smoke_api.py, 11 tests)
│   ├── unit/                   # 15 unit test files
│   └── system/                 # 4 end-to-end and performance test files
│
├── scripts/                    # 22 Python scripts + 1 shell script
│   ├── stage_0X_*.py           # Pipeline stage runners (01–07)
│   ├── NN_*.py                 # Alternate naming scheme (10, 20, 30, 40, 90) — see Section 7
│   ├── run_0_4.py              # Legacy meta-runner for stages 0–4
│   ├── demo_run.py             # In-process demo (TestClient, ~0.5s for 75 events)
│   ├── smoke_test.sh           # Idempotent local Docker smoke test
│   └── validation/             # Memory and performance validation scripts
│
├── templates/
│   └── index.html              # 5-section observability SPA (Phase 8 dashboard)
│
├── prometheus/
│   └── prometheus.yml          # Scrapes api:8000/metrics every 15s
│
├── grafana/
│   ├── dashboards/             # stage08_api_observability.json (5 panels) + backup copy
│   ├── provisioning/
│   │   ├── dashboards/         # File-based dashboard provisioning config
│   │   └── datasources/        # Prometheus datasource (uid=prometheus-stage8)
│   └── README.md
│
├── docs/                       # 23 markdown files across 4 subdirectories
│   ├── current_system/         # Architecture, implementation plan, project spec
│   ├── planning_and_analysis/  # Refactor plans, gap analysis, feasibility reviews
│   ├── refactor_progress/      # Phase 01–08 completion reports
│   ├── system_validation/      # System checks, test coverage, validation summary
│   ├── UI_ARCHITECTURE_SUMMARY.md  # Phase 8 UI docs (misplaced — see Section 7)
│   └── UI_USER_GUIDE.md            # Phase 8 UI docs (misplaced — see Section 7)
│
├── artifacts/
│   └── n8n_outbox/             # 180+ N8N webhook dry-run JSON files (untracked in git)
│
├── data/                       # All data files (gitignored)
│   ├── raw/                    # Original HDFS/BGL datasets
│   ├── processed/              # events_unified.csv (15.9M rows)
│   ├── intermediate/           # Templates, sequences, scores
│   ├── synth/                  # Synthetic generated logs
│   └── models/                 # Trained model artifacts
│
├── ai_workspace/               # Development workspace: stage scripts, reports, logs (gitignored)
├── reports/                    # Stage reports and analysis (gitignored)
├── examples/                   # N8N workflow stub
├── notebooks/                  # Placeholder (empty)
└── models/                     # Runtime model mount point (empty in git)
```

### Role of Each Key Directory

| Directory | Role |
|-----------|------|
| `src/api/` | FastAPI application: factory, routing, auth wiring, settings |
| `src/runtime/` | Real-time inference engine: rolling window buffer + model scoring |
| `src/alerts/` | Alert lifecycle: generation, deduplication, ring buffer, N8N dispatch |
| `src/modeling/` | All ML model code: baseline (IsolationForest) and transformer (LSTM) |
| `src/observability/` | Prometheus metrics registry and HTTP middleware |
| `src/security/` | API key authentication middleware |
| `src/health/` | Component health checking |
| `src/parsing/` | Log parsing, template mining, tokenization |
| `src/preprocessing/` | Feature preprocessing, GloVe embedding |
| `src/sequencing/` | Sequence construction from parsed events |
| `src/data/` | Synthetic data generation and LogEvent model |
| `src/data_layer/` | Data access layer (file loaders, ORM-like models) |
| `src/dataset/` | Dataset abstraction for training pipelines |
| `src/engine/` | High-level ProactiveEngine orchestrator |
| `src/synthetic/` | Duplicate synthetic generation (redundant — see Section 4) |
| `scripts/` | Pipeline stage runners and operational scripts |
| `templates/` | Frontend HTML for the observability dashboard |
| `prometheus/` | Prometheus scrape configuration |
| `grafana/` | Grafana provisioning (datasources, dashboards) |
| `docs/` | All project documentation |
| `tests/` | Full test suite (unit, integration, system, smoke) |
| `artifacts/` | N8N webhook dry-run outbox |

---

## 2. Configuration Consistency Report

### 2.1 Service Names and Ports

| Service | docker-compose name | Port mapping | Prometheus target |
|---------|--------------------|-----------|--------------------|
| FastAPI | `api` | `8000:8000` | `api:8000` |
| Prometheus | `prometheus` | `9090:9090` | N/A (self) |
| Grafana | `grafana` | `3000:3000` | N/A (pulls from prometheus) |

**Result: Consistent.** The service name `api` in docker-compose matches the scrape target hostname `api:8000` in `prometheus/prometheus.yml`. Ports are consistent throughout.

### 2.2 Health Check Configuration

```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 15s
  timeout: 5s
  retries: 5
  start_period: 30s
```

```dockerfile
# Dockerfile
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

**Issue:** `retries` differs — docker-compose sets `retries: 5`, Dockerfile sets `--retries=3`. When deployed via docker-compose, the compose value takes precedence. The Dockerfile value is only used for standalone container runs. Recommend aligning to a single value.

### 2.3 Volume Mounts

```yaml
# docker-compose.yml
volumes:
  - ./models:/app/models:ro
  - ./artifacts:/app/artifacts
```

```dockerfile
# Dockerfile
RUN mkdir -p models artifacts
```

**Observation:** The Dockerfile creates empty `models/` and `artifacts/` directories. docker-compose mounts local directories on top. This is correct for the demo flow. However, `artifacts/` is mounted read-write (no `:ro`) while `models/` is read-only. This is intentional — N8N outbox writes to `artifacts/n8n_outbox/`. No issue.

### 2.4 Grafana Datasource UID

```yaml
# grafana/provisioning/datasources/datasource.yml
uid: prometheus-stage8
```

The Grafana dashboard JSON (`stage08_api_observability.json`) references this UID in panel queries. As long as both files use `prometheus-stage8`, Grafana will auto-wire the datasource. This is consistent.

### 2.5 .env.example Stage Reference

The `.env.example` file includes a section labeled `# Stage 9.1 (Demo Mode)` containing:
```
DEMO_WARMUP_ENABLED
DEMO_WARMUP_EVENTS
DEMO_WARMUP_INTERVAL_SECONDS
```

**Issue:** The project is at Stage 8. "Stage 9.1" does not exist in the project roadmap. These variables are used by the Stage 8 docker-compose config (`DEMO_WARMUP_ENABLED: "true"`, `DEMO_WARMUP_EVENTS: "75"`). The section label in `.env.example` should be renamed to `# Stage 8 (Demo Mode)`.

### 2.6 Prometheus Scrape Interval

```yaml
# prometheus/prometheus.yml
scrape_interval: 15s
```

```yaml
# docker-compose.yml (prometheus retention)
--storage.tsdb.retention.time=7d
```

**Result: Consistent.** The 15-second scrape interval aligns with the Grafana dashboard panel queries which default to a 15s evaluation interval. No issue.

### 2.7 Summary of Configuration Issues

| Issue | Severity | Location |
|-------|----------|----------|
| `retries` mismatch (5 vs 3) between compose and Dockerfile | Low | `docker-compose.yml` / `Dockerfile` |
| `.env.example` section labeled "Stage 9.1" (should be "Stage 8") | Low | `.env.example` |

---

## 3. Metrics Consistency Report

### 3.1 Prometheus Metrics Inventory

All Prometheus metrics are defined in a single registry class: `src/observability/metrics.py → MetricsRegistry`.

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `ingest_events_total` | Counter | none | Events received at POST /ingest |
| `ingest_windows_total` | Counter | none | Windows emitted by InferenceEngine |
| `alerts_total` | Counter | `severity` | Alerts fired (labelled by severity level) |
| `ingest_errors_total` | Counter | none | Unhandled errors in /ingest handler |
| `ingest_latency_seconds` | Histogram | none | End-to-end /ingest latency |
| `scoring_latency_seconds` | Histogram | none | Model scoring latency per window |

### 3.2 Metric Naming Convention

Current pattern: `{subsystem}_{operation}_{unit_or_suffix}`

- `ingest_events_total` — follows Prometheus convention (noun_verb_total for counters)
- `ingest_windows_total` — consistent
- `alerts_total` — consistent
- `ingest_errors_total` — consistent
- `ingest_latency_seconds` — consistent (histogram with `_seconds` suffix)
- `scoring_latency_seconds` — consistent

**Issue — Missing namespace prefix:** Prometheus best practice recommends a service-level namespace prefix (e.g., `plae_` or `anomaly_engine_`) to prevent collision if the metrics are federated or aggregated with metrics from other services. Currently all metrics use bare names without a prefix.

Example fix: `ingest_events_total` → `plae_ingest_events_total`

**Severity:** Low. For a single-service deployment this is not a functional issue, but it is a naming best practice violation.

### 3.3 MetricsMiddleware Coverage Gap

`MetricsMiddleware.dispatch()` docstring says: *"Records HTTP request counts and latency for every route."*

However, the implementation only records latency for `POST /ingest`:
```python
if request.url.path == "/ingest" and request.method == "POST":
    metrics.ingest_latency_seconds.observe(elapsed)
```

Other routes (`GET /health`, `GET /alerts`, `GET /metrics`, `GET /`, `POST /query`) are not measured. The docstring is misleading. No general `http_requests_total` or per-route latency counter exists.

**Severity:** Low. Functionally correct for the current scope. Docstring should be corrected to say "Records latency for POST /ingest only."

### 3.4 No Duplicate Metrics

Since all metrics are registered inside a single `MetricsRegistry` class with a private `CollectorRegistry()`, there are no global registry duplicates. Tests create isolated instances. No `ValueError: Duplicated timeseries` risk in production.

### 3.5 Grafana Panel Queries vs Defined Metrics

| Grafana Panel | Query | Metric Defined |
|---------------|-------|---------------|
| Events ingestion rate | `rate(ingest_events_total[...])` | Yes |
| Window emission rate | `rate(ingest_windows_total[...])` | Yes |
| Alerts by severity | `rate(alerts_total{severity="..."}[...])` | Yes |
| Ingest latency p95 | `histogram_quantile(0.95, rate(ingest_latency_seconds_bucket[...]))` | Yes |
| Scoring latency p95 | `histogram_quantile(0.95, rate(scoring_latency_seconds_bucket[...]))` | Yes |

**Result: All Grafana panels reference defined metrics. No broken dashboard panels.**

### 3.6 Summary of Metrics Issues

| Issue | Severity | Location |
|-------|----------|----------|
| No namespace prefix on metric names | Low | `src/observability/metrics.py` |
| MetricsMiddleware docstring claims full route coverage but only covers /ingest | Low | `src/observability/metrics.py:99` |

---

## 4. Duplicate File Detection

### 4.1 Duplicate Synthetic Data Generation Modules

**Critical duplicate:** Two separate modules implement nearly identical synthetic data generation:

| Module | Files |
|--------|-------|
| `src/data/` | `synth_generator.py`, `synth_patterns.py`, `scenario_builder.py`, `log_event.py` |
| `src/synthetic/` | `generator.py`, `patterns.py`, `scenario_builder.py`, `__init__.py` |

Both modules generate synthetic BGL/HDFS log events with anomaly patterns. The `src/data/` module appears to be the integrated version (used by the API pipeline via `src/api/pipeline.py`), while `src/synthetic/` appears to be an earlier standalone version.

**Recommendation:** Confirm which module is imported by `pipeline.py` and tests, then deprecate the unused one (do not delete until confirmed).

### 4.2 Duplicate Grafana Dashboard Files

```
grafana/dashboards/stage08_api_observability.json
grafana/dashboards/Stage 08 API Observability-1772643247797.json
```

The second file (with timestamp suffix) appears to be an auto-exported backup from Grafana UI. The provisioning config (`dashboards.yml`) loads all `.json` files from this directory, meaning Grafana will attempt to provision both dashboards.

**Issue:** Grafana may show two dashboards with identical content or fail provisioning if UIDs collide.

**Recommendation:** Remove the backup file (`Stage 08 API Observability-1772643247797.json`) or move it outside the `grafana/dashboards/` directory. Keep only `stage08_api_observability.json`.

### 4.3 Duplicate Script Naming Schemes

The `scripts/` directory contains two parallel naming conventions for pipeline stages:

| Convention | Files | Coverage |
|------------|-------|----------|
| `stage_0N_*.py` | stage_01_data.py, stage_02_templates.py, ... stage_07_run_api.py | Stages 1–7 |
| `NN_*.py` | 10_download_data.py, 20_prepare_events.py, 30_build_sequences.py, 40_train_baseline.py, 90_run_api.py | Stages 1, 2, 3, 4, 7 |

The `NN_*.py` scripts appear to be simplified wrappers or earlier drafts of the `stage_0N_*.py` equivalents. Both sets exist simultaneously.

**Recommendation:** Consolidate to one convention (prefer `stage_0N_*.py` as it is more descriptive). The `NN_*.py` files can be removed after confirming they are not referenced in CI or documentation.

### 4.4 Duplicate API Runner Scripts

```
scripts/stage_07_run_api.py   # Full stage runner with argparse
scripts/90_run_api.py          # Simplified wrapper
main.py                        # Project entrypoint (delegates to stage_07_run_api.py)
```

Three entry points exist to start the API server. `main.py` delegates to `stage_07_run_api.py`. `90_run_api.py` is a parallel duplicate.

**Recommendation:** Keep `main.py` + `scripts/stage_07_run_api.py`. Remove `scripts/90_run_api.py`.

### 4.5 Duplicate Sequence/Stage Scripts

```
scripts/run_0_4.py             # Meta-runner: calls stages 01–04 sequentially
```

This script manually orchestrates stages 0–4. Its functionality is now superseded by individual stage scripts and CI. It is a legacy artifact.

**Recommendation:** Remove `scripts/run_0_4.py` or clearly label it as legacy.

### 4.6 Summary of Duplicates

| Duplicate | Severity | Action |
|-----------|----------|--------|
| `src/data/` vs `src/synthetic/` (synthetic generation) | High | Confirm active module; remove the other |
| Grafana backup dashboard JSON | Medium | Remove `Stage 08 API Observability-1772643247797.json` from dashboards dir |
| `NN_*.py` vs `stage_0N_*.py` scripts | Medium | Consolidate to `stage_0N_*.py` |
| `scripts/90_run_api.py` vs `scripts/stage_07_run_api.py` | Low | Remove `90_run_api.py` |
| `scripts/run_0_4.py` (meta-runner) | Low | Label as legacy or remove |

---

## 5. Unused File Detection

*Note: All items listed are candidates for cleanup. No deletions are recommended without confirming lack of import/reference.*

### 5.1 Empty or Placeholder Modules

| File | Observation |
|------|-------------|
| `src/app/__init__.py` | Module `src/app` has only an `__init__.py`. No other files. Appears to be an abandoned placeholder. |
| `src/core/contracts/__init__.py` | Same pattern — `src/core/contracts/` only contains `__init__.py`. No interface definitions. |
| `notebooks/` | Directory exists but contains no notebook files. Placeholder only. |

### 5.2 Likely Unused Scripts

| Script | Reason for Flagging |
|--------|---------------------|
| `scripts/run_0_4.py` | Legacy meta-runner superseded by individual stage scripts |
| `scripts/90_run_api.py` | Duplicate of `stage_07_run_api.py` |
| `scripts/stage_05_runtime_benchmark.py` | Benchmarking/profiling tool; not part of production pipeline |
| `scripts/stage_05_runtime_calibrate.py` | Standalone calibration; calibration is now embedded in InferenceEngine |
| `scripts/stage_05_runtime_demo.py` | Superseded by `scripts/demo_run.py` (newer, in-process) |
| `scripts/validation/run_memory_validation.py` | One-off validation script; not referenced in CI |
| `scripts/validation/run_performance_validation.py` | One-off validation script; not referenced in CI |

### 5.3 AI Workspace (Development Artifacts)

`ai_workspace/` contains per-stage development scripts, logs, and reports from the active development phase. These are gitignored and not shipped. They are retained for reproducibility but are not part of the production codebase.

**Recommendation:** Confirm `ai_workspace/` is fully covered by `.gitignore`. If so, no action needed — it is appropriately isolated.

### 5.4 N8N Outbox Files

`artifacts/n8n_outbox/` contains 180+ JSON files (N8N webhook dry-run outputs). These are untracked in git (shown as `??` in git status). They accumulate during every test run that exercises the N8N client in dry-run mode.

**Observation:** The `.gitignore` does not appear to exclude `artifacts/n8n_outbox/*.json`. If these files are unintentionally untracked (rather than gitignored), they will show up permanently as untracked in `git status`, adding noise.

**Recommendation:** Add `artifacts/n8n_outbox/` to `.gitignore` if these files should not be tracked. Alternatively, document them as intentional test artifacts.

### 5.5 Unused Engine Module

`src/engine/proactive_engine.py` — `ProactiveEngine` is listed as a "top-level orchestrator" but the actual request-time orchestration is handled by `src/api/pipeline.py`. Verify whether `ProactiveEngine` is imported anywhere in the active pipeline.

### 5.6 Summary of Unused Files

| File/Directory | Category | Recommended Action |
|----------------|----------|--------------------|
| `src/app/__init__.py` | Empty placeholder | Remove module directory |
| `src/core/contracts/__init__.py` | Empty placeholder | Remove or populate |
| `notebooks/` | Empty directory | Remove or add .gitkeep |
| `scripts/run_0_4.py` | Legacy runner | Remove or label legacy |
| `scripts/90_run_api.py` | Duplicate entrypoint | Remove |
| `scripts/stage_05_runtime_*.py` (benchmark/calibrate/demo) | Superseded scripts | Move to `scripts/archive/` |
| `scripts/validation/` | One-off scripts | Move to `scripts/archive/` |
| `artifacts/n8n_outbox/*.json` | Test artifacts | Add to `.gitignore` |
| `src/engine/proactive_engine.py` | Unverified integration | Audit imports before decision |

---

## 6. Documentation Coverage Analysis

### 6.1 Current Documentation Inventory

| Document | Location | Coverage |
|----------|----------|----------|
| README.md | Root | High-level overview, architecture diagram, tech stack, demo walkthrough |
| MASTER_ARCHITECTURE_AND_EXECUTION_PLAN.md | docs/current_system/ | Full system design and stage plan |
| SYSTEM_ARCHITECTURE.md | docs/current_system/ | Architecture details |
| PROJECT_SPECIFICATION.md | docs/current_system/ | Requirements and spec |
| IMPLEMENTATION_ROADMAP.md | docs/current_system/ | Stage-by-stage roadmap |
| UI_OBSERVABILITY_INVESTIGATION_CENTER.md | docs/current_system/ | UI design spec |
| AI_PIPELINE_REFACTOR_PLAN.md | docs/planning_and_analysis/ | Refactor planning |
| UPGRADE_FEASIBILITY_REVIEW.md | docs/planning_and_analysis/ | Feasibility analysis |
| PHASE_01 through PHASE_08 reports | docs/refactor_progress/ | Phase completion reports |
| SYSTEM_VALIDATION_SUMMARY.md | docs/system_validation/ | Validation summary |
| TEST_COVERAGE_REPORT.md | docs/system_validation/ | Test coverage |
| ADDITIONAL_SYSTEM_CHECKS_REPORT.md | docs/system_validation/ | System health checks |
| UI_ARCHITECTURE_SUMMARY.md | docs/ (root) | Phase 8 UI architecture |
| UI_USER_GUIDE.md | docs/ (root) | Phase 8 UI user guide |
| PHASE_08_UI_REPORT.md | docs/refactor_progress/ | Phase 8 completion |
| prometheus/README.md | prometheus/ | Prometheus config notes |
| grafana/README.md | grafana/ | Grafana dashboard notes |
| scripts/README.md | scripts/ | Pipeline stage descriptions |
| artifacts/README.md | artifacts/ | Artifact storage description |

### 6.2 Documentation Gaps

| Area | Gap | Priority |
|------|-----|----------|
| **API Reference** | No dedicated API reference doc listing all endpoints, request/response schemas, error codes, and authentication usage | High |
| **Alert System** | No dedicated document describing the alert lifecycle, ring buffer configuration, severity levels, cooldown logic, and N8N integration | High |
| **Security** | No dedicated security document describing the API key authentication model, public endpoint bypass, and production hardening guidance | Medium |
| **Data Pipeline** | No single document connecting all stages (01–07) in sequence with inputs/outputs for each | Medium |
| **Model Reference** | No document describing the baseline IsolationForest model, transformer model architecture, ensemble scoring formula, and threshold calibration | Medium |
| **Deployment Guide** | README covers Docker but lacks production deployment guidance (scaling, TLS, secret management, real model loading) | Medium |
| **Metrics Reference** | No dedicated metrics reference listing all Prometheus metrics with their type, labels, and example queries | Low |
| **Runbook** | No operational runbook for common scenarios (restart, model update, alert tuning, dashboard troubleshooting) | Low |

### 6.3 Documentation Structure Issue

`UI_ARCHITECTURE_SUMMARY.md` and `UI_USER_GUIDE.md` are located at `docs/` root rather than inside a subdirectory. They should be in `docs/current_system/` alongside `UI_OBSERVABILITY_INVESTIGATION_CENTER.md`.

---

## 7. Naming Standardization Suggestions

### 7.1 Script Naming Convention

**Current state:** Two conflicting conventions exist in `scripts/`:

| Convention | Example |
|------------|---------|
| `stage_0N_name.py` | `stage_01_data.py`, `stage_07_run_api.py` |
| `NN_name.py` | `10_download_data.py`, `90_run_api.py` |

**Recommendation:** Standardize on `stage_0N_name.py`. The `NN_*.py` files should be removed or renamed. The `stage_0N_*.py` convention is more readable and consistent with the project's stage-based structure.

### 7.2 Module Naming: src/data/ vs src/data_layer/ vs src/synthetic/

**Current state:** Three modules with overlapping names and purposes:

| Module | Actual Purpose |
|--------|---------------|
| `src/data/` | Synthetic log generation + LogEvent model |
| `src/data_layer/` | Data access (file loading, ORM-like models) |
| `src/synthetic/` | Duplicate synthetic generation (redundant) |

**Recommendation:**
- Rename `src/data/` to `src/synthetic_data/` or keep as `src/data/` but remove `src/synthetic/`
- Rename `src/data_layer/` to `src/storage/` or `src/data_access/` for clarity
- The distinction between "data" and "data_layer" is not obvious to a new reader

### 7.3 Grafana Dashboard File Names

**Current state:**
```
grafana/dashboards/stage08_api_observability.json           # Good: snake_case
grafana/dashboards/Stage 08 API Observability-1772643247797.json  # Bad: spaces + timestamp
```

**Recommendation:** Remove the backup file or rename to `stage08_api_observability_backup.json` and move outside `grafana/dashboards/`.

### 7.4 Prometheus Metric Namespace

**Current state:** No namespace prefix. All metrics use bare names (`ingest_events_total`).

**Recommendation:** Add a consistent namespace prefix. Suggested: `plae_` (Predictive Log Anomaly Engine).

| Current | Recommended |
|---------|-------------|
| `ingest_events_total` | `plae_ingest_events_total` |
| `ingest_windows_total` | `plae_ingest_windows_total` |
| `alerts_total` | `plae_alerts_total` |
| `ingest_errors_total` | `plae_ingest_errors_total` |
| `ingest_latency_seconds` | `plae_ingest_latency_seconds` |
| `scoring_latency_seconds` | `plae_scoring_latency_seconds` |

*Note: If Prometheus metrics are renamed, Grafana dashboard queries and all references must be updated atomically.*

### 7.5 Test File Naming

Most test files follow `test_*.py` convention. However, some use stage-specific prefixes:
```
test_stage_06_alert_policy.py
test_stage_06_dedup_cooldown.py
test_stage_07_auth.py
```

**Observation:** Stage prefixes are descriptive but may become confusing as the system evolves beyond the stage-based development model. Consider renaming to functional names:
```
test_alert_policy.py
test_alert_dedup.py
test_auth_middleware.py
```

### 7.6 .env.example Section Labels

Sections in `.env.example` are labeled by stage number (Stage 6, Stage 7, Stage 9.1). After the project is complete, these labels should be replaced with functional section names:
```
# === Alert Configuration ===
# === API Configuration ===
# === Demo Mode ===
```

### 7.7 Summary of Naming Issues

| Issue | Severity | Action |
|-------|----------|--------|
| Dual script naming (`stage_0N_*` vs `NN_*`) | Medium | Consolidate to `stage_0N_*` |
| `src/data/` vs `src/data_layer/` ambiguity | Medium | Rename one or both for clarity |
| `src/synthetic/` existence alongside `src/data/` | High | Resolve duplicate (Section 4) |
| Grafana backup file with spaces and timestamp | Medium | Remove from dashboards directory |
| No Prometheus metric namespace prefix | Low | Add `plae_` prefix |
| Stage-prefixed test file names | Low | Consider renaming to functional names |
| `.env.example` stage-number section labels | Low | Replace with functional section names |

---

## 8. Recommended Final Repository Structure

The following structure preserves all existing functionality while resolving the issues identified in this audit.

```
predictive-log-anomaly-engine/
│
├── README.md                       # High-level overview (keep as-is)
├── Dockerfile                      # Fix: align retries=5 with compose
├── docker-compose.yml              # Keep as-is
├── pyproject.toml                  # Keep as-is
├── requirements.txt                # Keep as-is
├── requirements-dev.txt            # Keep as-is
├── main.py                         # Keep as-is
│
├── .env.example                    # Fix: rename "Stage 9.1" → "Stage 8 / Demo Mode"
├── .dockerignore                   # Keep as-is
├── .gitignore                      # Fix: add artifacts/n8n_outbox/
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # Keep as-is
│
├── src/
│   ├── api/                        # Keep as-is
│   ├── runtime/                    # Keep as-is
│   ├── alerts/                     # Keep as-is
│   ├── modeling/                   # Keep as-is
│   │   ├── baseline/               # Keep as-is
│   │   └── transformer/            # Keep as-is
│   ├── observability/              # Fix: correct MetricsMiddleware docstring
│   ├── security/                   # Keep as-is
│   ├── health/                     # Keep as-is
│   ├── parsing/                    # Keep as-is
│   ├── preprocessing/              # Keep as-is
│   ├── sequencing/                 # Keep as-is
│   ├── data/                       # Keep as-is (confirm as canonical synthetic module)
│   ├── data_layer/                 # Consider renaming to storage/ or data_access/
│   ├── dataset/                    # Keep as-is
│   ├── engine/                     # Audit ProactiveEngine imports before keeping
│   │
│   │   # REMOVE or MERGE:
│   │   # src/synthetic/            → merge into src/data/ (duplicate)
│   │   # src/app/                  → remove empty placeholder
│   │   # src/core/contracts/       → populate or remove empty placeholder
│
├── scripts/
│   ├── stage_01_data.py            # Keep
│   ├── stage_01_synth_generate.py  # Keep
│   ├── stage_01_synth_to_processed.py  # Keep
│   ├── stage_01_synth_validate.py  # Keep
│   ├── stage_02_templates.py       # Keep
│   ├── stage_03_sequences.py       # Keep
│   ├── stage_04_baseline.py        # Keep
│   ├── stage_04_transformer.py     # Keep
│   ├── stage_05_run.py             # Keep
│   ├── stage_06_demo_alerts.py     # Keep
│   ├── stage_07_run_api.py         # Keep (primary API runner)
│   ├── demo_run.py                 # Keep (in-process demo)
│   ├── smoke_test.sh               # Keep
│   ├── README.md                   # Keep
│   │
│   ├── archive/                    # NEW: move legacy/non-production scripts here
│   │   ├── 10_download_data.py     # (was NN_*.py duplicate)
│   │   ├── 20_prepare_events.py
│   │   ├── 30_build_sequences.py
│   │   ├── 40_train_baseline.py
│   │   ├── 90_run_api.py
│   │   ├── run_0_4.py
│   │   ├── stage_05_runtime_benchmark.py
│   │   ├── stage_05_runtime_calibrate.py
│   │   ├── stage_05_runtime_demo.py
│   │   └── validation/
│
├── templates/
│   └── index.html                  # Keep as-is
│
├── prometheus/
│   └── prometheus.yml              # Keep as-is
│
├── grafana/
│   ├── dashboards/
│   │   └── stage08_api_observability.json  # Keep; REMOVE backup file with spaces/timestamp
│   ├── provisioning/
│   │   ├── dashboards/dashboards.yml       # Keep as-is
│   │   └── datasources/datasource.yml      # Keep as-is
│   └── README.md                           # Keep as-is
│
├── docs/
│   ├── current_system/
│   │   ├── MASTER_ARCHITECTURE_AND_EXECUTION_PLAN.md
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   ├── PROJECT_SPECIFICATION.md
│   │   ├── IMPLEMENTATION_ROADMAP.md
│   │   ├── UI_OBSERVABILITY_INVESTIGATION_CENTER.md
│   │   ├── UI_ARCHITECTURE_SUMMARY.md      # MOVE from docs/ root
│   │   └── UI_USER_GUIDE.md               # MOVE from docs/ root
│   │
│   ├── api/                               # NEW section
│   │   └── API_REFERENCE.md              # NEW: endpoints, schemas, auth, error codes
│   │
│   ├── operations/                        # NEW section
│   │   ├── ALERT_SYSTEM_GUIDE.md         # NEW: alert lifecycle, ring buffer, N8N
│   │   ├── SECURITY_GUIDE.md             # NEW: API key auth, production hardening
│   │   ├── DEPLOYMENT_GUIDE.md           # NEW: production deployment, TLS, scaling
│   │   └── METRICS_REFERENCE.md          # NEW: Prometheus metrics catalog
│   │
│   ├── planning_and_analysis/             # Keep as-is (historical)
│   ├── refactor_progress/                 # Keep as-is (historical)
│   └── system_validation/                 # Keep as-is
│
├── tests/
│   ├── test_pipeline_smoke.py              # Keep
│   ├── helpers_stage_07.py                 # Keep (consider renaming to helpers.py)
│   ├── test_stage_06_alert_policy.py       # Keep (consider renaming to test_alert_policy.py)
│   ├── test_stage_06_dedup_cooldown.py     # Keep (consider renaming)
│   ├── test_stage_06_n8n_outbox.py         # Keep (consider renaming)
│   ├── test_stage_07_auth.py               # Keep (consider renaming)
│   ├── test_stage_07_ingest_integration.py # Keep (consider renaming)
│   ├── test_stage_07_metrics.py            # Keep (consider renaming)
│   ├── integration/                        # Keep as-is
│   ├── unit/                               # Keep as-is
│   └── system/                             # Keep as-is
│
├── artifacts/
│   └── n8n_outbox/                         # Add to .gitignore
│
└── models/                                 # Keep as mount point (empty in git)
```

### Key Changes from Current Structure

| Change | Reason |
|--------|--------|
| Remove `src/synthetic/` | Duplicate of `src/data/` |
| Remove `src/app/` | Empty placeholder |
| Remove/populate `src/core/contracts/` | Empty placeholder |
| Move `NN_*.py` scripts to `scripts/archive/` | Duplicate naming convention |
| Move benchmark/calibrate/demo scripts to `scripts/archive/` | Not part of production pipeline |
| Remove `grafana/dashboards/Stage 08 API Observability-1772643247797.json` | Duplicate backup file |
| Add `artifacts/n8n_outbox/` to `.gitignore` | Test artifacts should not appear in git status |
| Move `UI_*.md` docs to `docs/current_system/` | Misplaced in docs root |
| Add `docs/api/API_REFERENCE.md` | Missing high-priority documentation |
| Add `docs/operations/` section | Missing operational documentation |
| Fix `.env.example` section label "Stage 9.1" | Incorrect stage reference |
| Fix Dockerfile `--retries=3` → `--retries=5` | Align with docker-compose |

---

## Executive Summary

The repository is in excellent functional condition — all 8 stages are complete, the test suite passes (211/233 fast tests), and the full Docker observability stack is operational. The audit identified no critical structural defects. The main areas requiring attention are:

**High Priority:**
1. `src/synthetic/` is a redundant duplicate of `src/data/` — confirm and remove the unused module
2. Grafana backup dashboard file (`Stage 08 API Observability-1772643247797.json`) may cause provisioning conflicts — remove from dashboards directory

**Medium Priority:**
3. Dual script naming convention (`stage_0N_*.py` vs `NN_*.py`) — consolidate to `stage_0N_*.py`
4. `artifacts/n8n_outbox/` is untracked in git, polluting `git status` — add to `.gitignore`
5. Missing documentation: API reference, alert system guide, security guide, deployment guide

**Low Priority:**
6. Minor config inconsistency: `retries` value differs between `Dockerfile` and `docker-compose.yml`
7. `.env.example` references non-existent "Stage 9.1" — relabel to "Stage 8"
8. Prometheus metrics lack namespace prefix (`plae_`) — best practice violation only
9. Empty placeholder modules (`src/app/`, `src/core/contracts/`, `notebooks/`) should be removed

No runtime logic changes are required or recommended.
