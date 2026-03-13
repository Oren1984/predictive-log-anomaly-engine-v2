# Repository Upgrade Feasibility Review
## Predictive Log Anomaly Engine — OOP AI Pipeline Refactor

**Review Date:** 2026-03-08
**Reviewer:** Claude Code (Automated Architectural Review)
**Scope:** Read-only analysis of five proposed upgrades against four core planning documents
**Status:** Final — No code was written or modified during this review

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Alignment with Core Documents](#2-alignment-with-core-documents)
3. [Upgrade Evaluation](#3-upgrade-evaluation)
   - [Word2Vec + FastText Experiment](#31-word2vec--fasttext-experiment)
   - [Preprocessing Improvements](#32-preprocessing-improvements)
   - [Fallback Strategy](#33-fallback-strategy)
   - [Missing UI Endpoints](#34-missing-ui-endpoints)
   - [Small Real-Server Deployment](#35-small-real-server-deployment)
4. [FastText Positioning Recommendation](#4-fasttext-positioning-recommendation)
5. [Risk of Scope Drift](#5-risk-of-scope-drift)
6. [Final Recommendation](#6-final-recommendation)

---

## 1. Executive Summary

Five upgrades were evaluated against the current repository state and four planning documents: the Implementation Action Plan (IAP), the Project Refactor Requirements (PRR), the Repository Gap Analysis (RGA), and the UI Observability Investigation Center specification (UIC).

| Upgrade | Decision | Rationale |
|---|---|---|
| Word2Vec default + FastText as experiment | **Approved — Experimental only** | PRR explicitly names both; FastText as a benchmark does not disrupt architecture |
| Preprocessing improvements | **Approved — Phase 2 scope** | Directly planned in IAP Phase 2; existing regex patterns are a starting point only |
| Fallback strategy (parallel pipelines) | **Approved — Already planned** | IAP Section 8 explicitly mandates this approach; no new design needed |
| Missing UI endpoints | **Approved — Phase 8 scope** | All four endpoints are explicitly required by UIC; planned in IAP Phase 8 |
| Small real-server deployment | **Deferred** | Docker Compose already exists; HTTPS/reverse proxy is a deployment concern, not a blocker for the AI refactor |

No upgrade reviewed here is architecturally incompatible or should be rejected outright. The primary risk is not that any individual upgrade is harmful, but that implementing several of them before the core AI pipeline refactor (Phases 1-7) is complete would dilute focus and introduce scope drift.

---

## 2. Alignment with Core Documents

### IMPLEMENTATION_ACTION_PLAN.md (IAP)

The IAP is the master execution roadmap. It defines eight sequential phases, from architecture alignment (Phase 1) through UI preparation (Phase 8). Its key architectural commitments are:

- LSTM is the main sequence model (Phase 4)
- Word2Vec is the primary embedding model (Phase 2), with FastText named as an alternative option
- IsolationForest and Transformer are kept as parallel fallbacks throughout transition
- New AI components are added as a new inference mode (`autoencoder`), not as replacements that break existing modes
- Three new API endpoints (`/ws/alerts`, `/pipeline/status`, `/score/history`) are explicitly planned in Phase 8

**Alignment of proposed upgrades:** Four of the five upgrades map directly onto planned IAP phases. The fallback strategy is not just aligned — it is the IAP's own stated approach. The only upgrade without a direct IAP mapping is the real-server deployment (reverse proxy + HTTPS), which is a deployment-layer concern sitting outside the AI refactor scope.

### PROJECT_REFACTOR_REQUIREMENTS_OOP_AI_PIPELINE.md (PRR)

The PRR defines the six-stage pipeline specification and its six required class names. It explicitly lists both **Word2Vec** and **FastText** as valid embedding models for Stage 1 (LogPreprocessor), which is the most important alignment point for this review. The PRR does not prescribe which embedding backend should be primary — it treats them as equivalent options. The PRR also defines the LSTM as the Stage 3 sequence model without alternatives, meaning the sequence modeling architecture is fixed.

**Alignment of proposed upgrades:** Word2Vec + FastText experiment aligns directly with PRR's explicit wording. Preprocessing improvements align with PRR's Stage 1 text-cleaning requirements. Fallback strategy aligns with PRR's goal of pipeline stability. UI endpoints align with PRR's "readiness for a future UI layer" requirement. Real-server deployment aligns with PRR's Stage 6 AIOps infrastructure objective.

### REPOSITORY_GAP_ANALYSIS_OOP_AI_PIPELINE.md (RGA)

The RGA is a diagnostic document that confirmed all four proposed UI endpoints are missing from the current codebase. Specifically, the RGA confirms:

- `LogPreprocessor` does not exist; Word2Vec/FastText are "not referenced anywhere in the project"
- The current text normalization (`TemplateMiner._SUBS`) covers basic patterns but stops at regex-based template IDs — it does not produce NLP-quality normalized text suitable for word embedding
- `/pipeline/status`, `/score/history`, `/ws/alerts`, and `/alerts/{alert_id}` are all absent from `src/api/routes.py`
- The existing pipeline has no fallback or parallel-mode mechanism — the IAP's parallel-mode design fills this gap

**Alignment of proposed upgrades:** All five upgrades address genuine gaps confirmed by the RGA. None of the upgrades contradict or undermine the RGA's findings. The upgrades are remedial responses to diagnosed deficiencies.

### UI_OBSERVABILITY_INVESTIGATION_CENTER.md (UIC)

The UIC is the most specific document for the UI endpoint upgrade evaluation. It explicitly names all four missing endpoints as required API surface for the five UI panels:

| Endpoint | Required by UIC panel | Current status |
|---|---|---|
| `GET /pipeline/status` | Panel 4 — Pipeline Component Status | Missing |
| `GET /score/history` | Panel 3 — Score Timeline | Missing |
| `GET /alerts/{alert_id}` | Panel 5 — RAG Investigation | Missing |
| `GET /ws/alerts` | Panel 2 — Live Alert Feed | Missing |

The UIC also explicitly states the UI is a read-only observability layer, not an admin panel. This boundary condition constrains how UI endpoints should be designed: they expose data, not controls. The UIC's architectural constraints are fully consistent with the proposed upgrade (the request is to add the missing endpoints, not to add write or control endpoints).

---

## 3. Upgrade Evaluation

### 3.1 Word2Vec + FastText Experiment

**Proposal:** Keep Word2Vec as the production default embedding model. Add FastText as a side experiment or benchmark only — not as a migration path or production replacement.

**1. Compatibility with current architecture:**
Fully compatible. Neither Word2Vec nor FastText exists in the current codebase. The new `LogPreprocessor` class (to be built in Phase 2) is the correct insertion point. The `gensim` library provides both models with nearly identical Python APIs, so the `LogPreprocessor` can support both via a backend parameter without changing any downstream component.

**2. Alignment with original specification (PRR):**
Direct alignment. PRR's architecture table explicitly lists "Word2Vec, FastText" under the NLP Embedding stage. The specification does not prescribe one over the other.

**3. Alignment with the refactor plan (IAP):**
Aligned. IAP Phase 2 names Word2Vec as the implementation target and proposes `models/word2vec.model` as the artifact path. FastText as an experimental parallel adds one artifact (`models/fasttext.model`) without changing Phase 2's scope or tasks.

**4. Alignment with UI observability design (UIC):**
The UIC references the embedding model only in Panel 4 (Pipeline Component Status), which shows which model file is loaded. Supporting both Word2Vec and FastText would require the `GET /pipeline/status` response to report the active backend. This is a minor addition to the response schema, not a structural change.

**5. Can it be added without breaking the system?**
Yes. FastText as an experiment does not touch any existing code. It adds one training run and one model artifact. The key guard is that it must not replace Word2Vec as the default without comparative evaluation.

**6. Benefits:**
- FastText handles out-of-vocabulary (OOV) tokens via character n-grams, which is especially valuable for BGL logs where hex addresses, node IDs, and error codes produce tokens not seen during training
- Provides a built-in comparison baseline to evaluate whether semantic embedding quality affects downstream LSTM and Autoencoder performance
- Keeps the project aligned with both embedding options named in PRR without over-engineering

**7. Risks:**
- FastText models are larger on disk than equivalent Word2Vec models (character n-gram storage)
- Training time is slightly longer (character-level computation)
- If FastText produces measurably better results, it creates pressure to make it the default, which would require updating the IAP and re-running downstream training

**8. Disadvantages:**
- Doubles the embedding training time during Phase 2
- Requires a comparison evaluation script before a production decision can be made
- Adds a `models/fasttext.model` artifact that must be managed alongside `models/word2vec.model`

**9. Dependencies:**
- `gensim>=4.3.0` (supports both Word2Vec and FastText; single library addition to `requirements.txt`)
- Phase 2 must be complete before FastText experiment can run

**10. Decision: APPROVED — Experimental only**

FastText should be trained and benchmarked during or after Phase 2, using the same log corpus as Word2Vec. The results should be documented in a brief comparison report before any production promotion. Word2Vec remains the default until measurable evidence justifies a change.

---

### 3.2 Preprocessing Improvements

**Proposal:** Improve the text normalization stage with better handling of IP addresses, timestamps, IDs, service names, and error codes.

**1. Compatibility with current architecture:**
Fully compatible. The existing normalization logic lives in `TemplateMiner._SUBS` (nine regex substitutions in `src/parsing/template_miner.py`). The IAP explicitly instructs Phase 2 to port these patterns into `LogPreprocessor.clean()`. Improving the patterns as part of that porting work is a scoped enhancement, not an architectural change.

**2. Alignment with original specification (PRR):**
Direct alignment. PRR Stage 1 explicitly defines a "Text Cleaner" component responsible for removing irrelevant characters and normalizing variables, with examples including "IP addresses -> [IP]" and "Dates -> [TIMESTAMP]". The current `_SUBS` patterns are a minimal implementation of this requirement.

**3. Alignment with the refactor plan (IAP):**
Aligned. IAP Phase 2 Task 2 states: "Implement `LogPreprocessor.clean()` — port regex patterns from `src/parsing/template_miner.py`." The word "port" implies a direct copy, but the word "implement" leaves room for improvement. Enhancing the patterns during Phase 2 is within scope.

**4. Alignment with UI observability design (UIC):**
Indirect alignment. Better normalization produces more semantically consistent embeddings, which produces more reliable reconstruction errors, which produces more accurate alert evidence. The UIC's Panel 5 (RAG Investigation) relies on alert evidence quality — better normalization strengthens that evidence.

**5. Can it be added without breaking the system?**
Yes. Normalization lives entirely inside `LogPreprocessor.clean()`, which does not exist yet. The improvement is additive and isolated.

**6. Benefits:**
- IPv6 normalization (current patterns only handle IPv4)
- ISO 8601 and epoch timestamp variants beyond the current single pattern
- Session/block/transaction ID formats beyond `blk_` prefix (which is HDFS-specific)
- Service name canonicalization (uppercase/lowercase variants, hyphen/underscore differences)
- Error code formats (e.g., `ENOENT`, `EIO`, Windows event IDs)
- Better normalization directly improves embedding quality: semantically identical log lines with different numeric IDs will produce more similar vectors

**7. Risks:**
- Over-aggressive normalization can collapse semantically distinct tokens (e.g., normalizing all hex values to `<HEX>` hides differences between error codes and memory addresses)
- New regex patterns require validation against both BGL and HDFS log corpora to avoid regressions
- Character-level FastText (if used) partially compensates for OOV tokens, reducing the urgency of normalization improvements

**8. Disadvantages:**
- Regex pattern development and testing takes time
- Must be validated against actual log samples from both datasets before committing
- Risk of over-normalization is real: if too much information is collapsed, the Word2Vec model cannot learn meaningful distinctions

**9. Dependencies:**
- None beyond Phase 2 itself
- Access to representative samples from `data/processed/events_unified.csv` for pattern testing

**10. Decision: APPROVED — Phase 2 scope**

Preprocessing improvements should be implemented as part of Phase 2's `LogPreprocessor.clean()` method, not as a separate preliminary task. The improvement scope should be bounded: focus on patterns confirmed to appear in the BGL and HDFS datasets, and validate each pattern against real samples before inclusion.

---

### 3.3 Fallback Strategy

**Proposal:** Keep the previous pipeline available in parallel during migration. Allow rollback if instability occurs.

**1. Compatibility with current architecture:**
Fully compatible. The `InferenceEngine` already supports multiple scoring modes (`baseline`, `transformer`, `ensemble`) selected via the `MODEL_MODE` environment variable. Adding an `autoencoder` mode as a new parallel path is architecturally consistent with the existing design.

**2. Alignment with original specification (PRR):**
Aligned. PRR's focus is on building the new pipeline; it does not prescribe how to handle the transition. The fallback strategy is an operational safeguard that complements the PRR's goals.

**3. Alignment with the refactor plan (IAP):**
Direct alignment. IAP Section 8 (Final Recommendation) states explicitly:

> "The existing IsolationForest model and NextTokenTransformerModel should be kept as operational fallbacks, not deleted."
> "The new architecture must be built as a new parallel code path inside InferenceEngine (a new autoencoder mode) rather than modifying the existing baseline/transformer modes. Keep old modes working throughout the transition."

This upgrade is not new — it is the IAP's own stated strategy. Approving it here means confirming that no deviation from this approach should be introduced.

**4. Alignment with UI observability design (UIC):**
The UIC's Panel 4 (Pipeline Component Status) displays the active `MODEL_MODE`. A fallback strategy means the UI must be able to show any of four modes: `baseline`, `transformer`, `ensemble`, `autoencoder`. This is a display concern, not an architectural one.

**5. Can it be added without breaking the system?**
Yes, by definition — the fallback strategy is the mechanism that prevents breaks. Old model artifacts (`models/baseline.pkl`, `models/transformer.pt`) remain on disk throughout Phases 2-7. The 22 slow tests that depend on these artifacts continue to pass.

**6. Benefits:**
- Zero-downtime migration: the system never has a period where no model is available
- Comparative evaluation: both old and new modes can score the same input, enabling direct performance comparison on the BGL/HDFS datasets
- Rollback capability: if the new autoencoder pipeline underperforms, `MODEL_MODE=baseline` restores the previous behavior with a single environment variable change and container restart
- Existing 22 slow tests and 211 fast tests continue to pass throughout the transition

**7. Risks:**
- Maintaining three or four scoring modes increases cognitive complexity inside `InferenceEngine`
- Each mode must be kept working as code evolves, which is ongoing maintenance overhead
- The risk of modes diverging in behavior grows over time if not actively tested

**8. Disadvantages:**
- Old model files must remain on disk longer, increasing artifact storage requirements
- The fallback modes must be explicitly listed in `Settings` as valid values for `MODEL_MODE`, requiring documentation
- Once the new pipeline is validated and the old models are deprecated, cleanup of fallback code paths requires a dedicated task

**9. Dependencies:**
- None — this is already the planned approach
- Requires that `Settings.MODEL_MODE` continue to accept `baseline`, `transformer`, and `ensemble` values throughout all phases

**10. Decision: APPROVED — Already planned**

This upgrade requires no new design decisions. It should be implemented exactly as IAP Section 8 prescribes. The only action required is to ensure no future implementation decision inadvertently deviates from the parallel-mode approach (for example, by deleting old model files during Phase 5 or 6).

---

### 3.4 Missing UI Endpoints

**Proposal:** Add four endpoints not yet present in `src/api/routes.py`:
- `GET /pipeline/status`
- `GET /score/history`
- `GET /alerts/{alert_id}`
- `GET /ws/alerts`

**1. Compatibility with current architecture:**
All four are compatible with the FastAPI application factory (`src/api/app.py`), the existing routing pattern (`src/api/routes.py`), and the authentication middleware (`src/security/auth.py`). WebSocket support is built into FastAPI/Starlette without additional dependencies.

**2. Alignment with original specification (PRR):**
The PRR specifies "readiness for a future UI layer" as a Stage 6 requirement. Adding these endpoints directly enables that readiness.

**3. Alignment with the refactor plan (IAP):**
Direct alignment. IAP Phase 8 explicitly lists three of the four endpoints as tasks:
- Task 1: `GET /ws/alerts` WebSocket endpoint
- Task 2: `GET /pipeline/status` endpoint
- Task 3: `GET /score/history` endpoint

`GET /alerts/{alert_id}` is not listed as an explicit Phase 8 task in the IAP, but it is required by UIC Panel 5 (RAG Investigation) and follows naturally from the existing `GET /alerts` endpoint pattern. It should be added alongside the three explicitly planned endpoints.

**4. Alignment with UI observability design (UIC):**
Direct and essential alignment. The UIC cannot be implemented without these endpoints. The UIC explicitly maps each panel to its backing endpoint:

| UIC Panel | Endpoint | IAP Phase |
|---|---|---|
| Panel 2 — Live Alert Feed | `GET /ws/alerts` | Phase 8 Task 1 |
| Panel 3 — Score Timeline | `GET /score/history` | Phase 8 Task 3 |
| Panel 4 — Pipeline Status | `GET /pipeline/status` | Phase 8 Task 2 |
| Panel 5 — RAG Investigation | `GET /alerts/{alert_id}` | Implied by UIC |

**5. Can it be added without breaking the system?**
Yes. All four are additive endpoints. They do not modify existing endpoints, schemas, or middleware. Authentication applies to all non-public endpoints consistently via `AuthMiddleware`.

**6. Benefits:**
- Unblocks the entire UIC implementation (four of five UI panels cannot be built without these)
- `/score/history` provides a ring buffer of `RiskResult` objects that enables operational trend analysis without querying Prometheus
- `/ws/alerts` eliminates the need for UI polling, reducing latency between alert firing and UI display
- `/pipeline/status` exposes model load state in a structured, machine-readable format that tooling can consume beyond the UI
- `/alerts/{alert_id}` enables deep investigation of individual alerts, supporting the RAG investigation workflow

**7. Risks:**
- `GET /ws/alerts` requires the WebSocket connection to be managed correctly (connection lifecycle, client disconnect handling). This is a small but non-trivial implementation concern.
- `GET /score/history` requires a new ring buffer (`_score_buffer`) in `Pipeline` or `ProactiveMonitorEngine`. This buffer must be threadsafe and size-bounded (suggested: `SCORE_HISTORY_SIZE` env var, default 500)
- `GET /pipeline/status` response schema is partially blocked on Phase 7 (`ProactiveMonitorEngine` must exist before per-component status is meaningful). A simplified version showing current `InferenceEngine` mode can be returned before Phase 7.

**8. Disadvantages:**
- Full `/pipeline/status` implementation requires Phase 7 (`ProactiveMonitorEngine`) to be complete for meaningful per-component data
- `GET /ws/alerts` adds a stateful connection type to the API that behaves differently from REST endpoints (connection management, reconnection logic client-side)
- Extending the public endpoint list (`PUBLIC_ENDPOINTS` in `settings.py`) must be done carefully to avoid accidentally bypassing authentication for sensitive endpoints

**9. Dependencies:**
- `GET /pipeline/status` (simplified): no new dependencies — can be implemented now against existing `Pipeline` class
- `GET /score/history`: requires adding `_score_buffer` to `Pipeline`/`ProactiveMonitorEngine` and wiring it in `process_event()`
- `GET /alerts/{alert_id}`: requires the alert ring buffer to be indexed by `alert_id` (currently it is a deque; needs an O(1) lookup structure alongside it, or a linear scan is acceptable given small buffer size of 200)
- `GET /ws/alerts`: no new Python dependencies — Starlette WebSocket support is already part of FastAPI's dependency tree

**10. Decision: APPROVED — Phase 8 scope**

All four endpoints should be implemented in Phase 8 as planned. However, simplified versions of `/pipeline/status` and `/score/history` can be introduced in Phase 7 (engine integration) to allow early UI testing. The complete, per-component status response is only meaningful after `ProactiveMonitorEngine` is built.

---

### 3.5 Small Real-Server Deployment

**Proposal:** Add to the existing deployment: a reverse proxy (nginx), HTTPS with TLS certificates, and basic API authentication. No Kubernetes. No major infrastructure changes.

**1. Compatibility with current architecture:**
Compatible. The current `docker-compose.yml` runs three services (`api`, `prometheus`, `grafana`). Adding an `nginx` service as a fourth container for TLS termination is a standard Docker Compose pattern. API authentication already exists via `AuthMiddleware` (`X-API-Key` header). Adding HTTPS does not change the authentication logic.

**2. Alignment with original specification (PRR):**
Partial alignment. PRR Stage 6 (AIOps Infrastructure) mentions Prometheus and Grafana but does not specify TLS or a reverse proxy. PRR's deployment requirements are implied rather than explicit.

**3. Alignment with the refactor plan (IAP):**
The IAP explicitly states: "Docker Compose: No changes needed." This is stated in the "What Can Stay As-Is" table. Adding an nginx reverse proxy service technically modifies `docker-compose.yml`, which creates a minor tension with this IAP statement.

However, the IAP's intent is that the monitoring and deployment infrastructure should not be disrupted during the AI refactor. Adding a reverse proxy after the refactor is complete does not conflict with this intent, as long as it is implemented after Phases 1-7 are stable.

**4. Alignment with UI observability design (UIC):**
The UIC specifies that the UI communicates with the API via HTTP/WebSocket. HTTPS deployment would require the UI's API base URL to change from `http://` to `https://`. This is a configuration-level change, not an architectural one. The UIC does not prescribe or restrict the transport layer.

**5. Can it be added without breaking the system?**
Yes, if introduced after the AI refactor is complete. Introducing it during the refactor (before Phase 7) risks destabilizing the CI/CD smoke test, which currently tests against `http://localhost:8000`. HTTPS would require certificate provisioning steps in CI that add complexity without benefit at that stage.

**6. Benefits:**
- HTTPS eliminates credential exposure risk for the `X-API-Key` header in transit
- Reverse proxy enables standard features: rate limiting, request buffering, log aggregation, routing to multiple services under one port (80/443)
- Makes the system production-ready for external exposure without requiring Kubernetes
- Aligns with professional deployment standards for a monitoring system that handles potentially sensitive operational data

**7. Risks:**
- TLS certificate management (self-signed vs. Let's Encrypt) requires additional setup and renewal logic in CI
- If added before Phase 7 is stable, nginx configuration errors can block the CI smoke test
- WebSocket connections (`/ws/alerts`) require nginx `proxy_pass` to explicitly enable WebSocket upgrade headers; incorrect configuration silently breaks WebSocket without error

**8. Disadvantages:**
- Adds one more service to manage in `docker-compose.yml`
- CI workflow must be updated to test against HTTPS (or bypass TLS in smoke tests, which partially defeats the purpose)
- Self-signed certificates require clients to accept certificate warnings or trust the CA explicitly
- Let's Encrypt certificates require a domain name and public internet access during issuance

**9. Dependencies:**
- `nginx:alpine` or equivalent Docker image (no new Python dependencies)
- TLS certificates (self-signed for local/dev, Let's Encrypt for production)
- Updated CI smoke test to handle HTTPS or to test only at the nginx HTTP-to-HTTPS redirect level
- Phase 7 must be complete (stable pipeline) before this is introduced

**10. Decision: DEFERRED**

The deployment upgrade is architecturally sound and desirable for production hardening, but it should be implemented after Phase 7 is complete and stable. Introducing HTTPS and a reverse proxy during the active AI refactor adds CI complexity without contributing to the refactor's goals. It should be tracked as a post-Phase-8 deployment task.

---

## 4. FastText Positioning Recommendation

### Summary Verdict: Keep FastText Experimental — Do Not Integrate into Production Pipeline Now

### Detailed Analysis

**What FastText is:**
FastText (Facebook Research, 2016) is a word embedding model that extends Word2Vec by representing each token as a sum of its character n-gram vectors. This means tokens not seen during training (OOV tokens) receive non-zero embeddings derived from their character composition, rather than being mapped to a zero vector or a random fallback.

**Why FastText is appealing for this project:**
The BGL dataset produces logs with highly variable tokens: hex memory addresses (`0x7f3a8b2c`), node identifiers (`R01-M0-N0-C:J13`), device paths, and numeric error codes. After normalization, many of these collapse to `<HEX>`, `<NODE>`, `<PATH>`, `<NUM>` — but normalization is imperfect. Tokens that escape normalization will appear as OOV entries in a pure Word2Vec model. FastText's character n-gram approach handles these residual OOV tokens gracefully.

**Why FastText should not go directly to production:**
Three reasons argue against immediate production integration:

1. **No performance evidence exists.** The project has never trained any embedding model. Before replacing Word2Vec with FastText (or choosing between them), both must be trained on the log corpus and their downstream impact on LSTM + Autoencoder performance must be measured. The right comparison metric is reconstruction error separability between normal and anomalous sequences on the BGL and HDFS validation sets — not embedding intrinsic metrics like cosine similarity.

2. **FastText adds model complexity without guaranteed payoff.** The character n-gram storage makes FastText models larger than equivalent Word2Vec models. For the BGL/HDFS log domain (dominated by structured, repetitive patterns), the OOV handling benefit may be marginal after good normalization is in place. If `LogPreprocessor.clean()` is implemented correctly (normalizing IPs, hex values, node IDs, paths), most of the problematic OOV tokens are removed before embedding. FastText's main advantage shrinks when preprocessing quality is high.

3. **IAP Phase 2 specifies Word2Vec.** Substituting FastText in Phase 2 without performance evidence deviates from the IAP without justification. The IAP's word "or FastText" is a PRR option, not an instruction to implement FastText in Phase 2. The IAP's training script target is `models/word2vec.model`.

**Architectural implications of adding FastText:**
If FastText is added as an experiment, the `LogPreprocessor` class needs a `backend` parameter: `"word2vec"` (default) or `"fasttext"`. The `embed()` method branches on this parameter. The `save()` and `load()` methods must handle both model types (gensim uses different class names: `Word2Vec` vs. `FastText`). The `GET /pipeline/status` API response should report which backend is active.

This design is clean and maintainable. It does not require any changes to `LogDataset`, `SystemBehaviorModel`, `AnomalyDetector`, or `SeverityClassifier`, because all of those operate on float vectors — they are agnostic to how those vectors were produced.

**Recommended positioning:**

| Path | Recommended? | When |
|---|---|---|
| Train Word2Vec in Phase 2 (IAP-specified) | Yes | Phase 2 |
| Train FastText as a parallel experiment during Phase 2 | Yes | Phase 2, after Word2Vec is working |
| Compare reconstruction error separability on validation set | Yes | After Phase 5 (AnomalyDetector) |
| Promote FastText to default if measurably better | Conditional | After comparison; only if evidence supports it |
| Replace Word2Vec with FastText without comparison | No | Never |

FastText should be presented as **future-ready experimental infrastructure** — trained, benchmarked, and available for promotion, but not the default until evidence justifies it.

---

## 5. Risk of Scope Drift

The five proposed upgrades are individually modest. The risk is not that any single upgrade is harmful — it is that implementing them out of order, or simultaneously with the active AI refactor, fragments engineering attention across too many workstreams.

**The primary risk of scope drift in this project is this:**

The core AI pipeline (Phases 1-7) is a sequential dependency chain. Each phase depends on the output of the previous phase:
- Phase 3 (LogDataset) cannot run without Phase 2 (Word2Vec embeddings)
- Phase 4 (LSTM) cannot train without Phase 3 (DataLoader)
- Phase 5 (Autoencoder) cannot train without Phase 4 (context vectors)
- Phase 6 (MLP) cannot train without Phase 5 (latent vectors)
- Phase 7 (ProactiveMonitorEngine) cannot be wired without Phases 1-6

Introducing a side workstream — such as FastText integration, preprocessing refinement, or HTTPS deployment — before Phase 4 or Phase 5 is complete creates the following failure modes:

**Failure Mode 1: Embedding model drift.** If FastText experiments run during Phase 2 but produce different vector dimensions or vocabulary than Word2Vec, the LogDataset (Phase 3) and SystemBehaviorModel (Phase 4) may need to be retrained when the embedding backend is changed. This multiplies training runs.

**Failure Mode 2: Test fragility.** Adding new endpoints (`/pipeline/status`, `/score/history`) before `ProactiveMonitorEngine` exists means those endpoints must be backed by incomplete or stub implementations. If tests are written against stub behavior, they may require rewriting after Phase 7 changes the underlying data.

**Failure Mode 3: Deployment pipeline instability.** Adding nginx and HTTPS to `docker-compose.yml` before Phase 7 is stable means the CI smoke test must be updated to handle HTTPS certificate negotiation. This is unnecessary complexity during a phase when the primary goal is LSTM and Autoencoder training.

**Failure Mode 4: Attention fragmentation.** Each approved-but-premature upgrade creates a partially-complete feature that requires context-switching to maintain. The cognitive cost of maintaining four half-done workstreams alongside active AI model development is underestimated.

**The boundary condition is clear:** Upgrades should be introduced in the phase where they are planned, not before. The approved upgrades are safe and aligned — their timing is the variable that determines whether they contribute to stability or introduce drift.

---

## 6. Final Recommendation

### Upgrades Approved for Immediate Implementation (within their planned phases)

| Upgrade | When to implement | Phase |
|---|---|---|
| **Preprocessing improvements** | During `LogPreprocessor.clean()` implementation | Phase 2 |
| **FastText as parallel experiment** | After Word2Vec training script is working | Phase 2 |
| **Fallback strategy (parallel modes)** | During `InferenceEngine` scoring path extension | Phase 5 |
| **`GET /pipeline/status` (simplified)** | During ProactiveMonitorEngine wiring | Phase 7 |
| **`GET /score/history`** | During Pipeline score buffer addition | Phase 7-8 |
| **`GET /alerts/{alert_id}`** | During Phase 8 endpoint additions | Phase 8 |
| **`GET /ws/alerts`** | During Phase 8 WebSocket implementation | Phase 8 |

### Upgrades That Should Remain Optional or Conditional

| Upgrade | Condition for promotion |
|---|---|
| **FastText as production default** | Only if post-Phase-5 benchmark shows measurably better reconstruction error separability on BGL/HDFS validation sets compared to Word2Vec |

### Upgrades That Should Be Deferred

| Upgrade | Reason for deferral |
|---|---|
| **Small real-server deployment (nginx + HTTPS)** | No blocker for the AI refactor; should be addressed as a post-Phase-8 deployment hardening task after the pipeline is confirmed stable |

### What Must Not Change

| Component | Constraint |
|---|---|
| **LSTM as main sequence model** | Non-negotiable; defined in PRR and IAP Phase 4 |
| **Transformer/IsolationForest as fallbacks** | Must remain available until new pipeline is validated |
| **Word2Vec as Phase 2 default** | FastText experiment does not change the default |
| **UI as read-only observability layer** | New endpoints must be read-only; no write or control endpoints |
| **`docker-compose.yml` stability** | Do not modify until after Phase 7 is complete and CI is green |
| **233 existing tests** | Must continue passing throughout all phases; mark new model-dependent tests `@pytest.mark.slow` |

### Priority Order

If implementation bandwidth is limited, the recommended priority sequence for the approved upgrades is:

1. **Phase 2 preprocessing improvements** — foundational; all downstream model quality depends on embedding quality
2. **Phase 2 FastText experiment** — low cost alongside Word2Vec training; gensim provides both in a single library
3. **Phase 5 fallback strategy** — critical for operational stability; enables rollback without downtime
4. **Phase 8 UI endpoints** — unblocks the UIC implementation; implement all four together
5. **Post-Phase-8 real-server deployment** — deferred; production hardening after system is confirmed stable

The core guidance is: **follow the IAP phase sequence, introduce each upgrade within its intended phase, and do not allow any upgrade to advance ahead of the phase boundary it depends on.**

---

*This document is analysis only. No code was written, no files were modified, and no refactoring was performed during this review.*
