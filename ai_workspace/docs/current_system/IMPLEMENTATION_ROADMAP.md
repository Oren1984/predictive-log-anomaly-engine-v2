# IMPLEMENTATION_ROADMAP.md
## Predictive Log Anomaly Engine — Implementation Roadmap

**Version:** 1.0  
**Date:** 2026-03-08  
**Status:** Working Roadmap  
**Project:** Predictive Log Anomaly Engine

---

## 1. Purpose

This roadmap defines the agreed implementation order for the next development phase of the Predictive Log Anomaly Engine.

Its purpose is to translate the approved architecture into a practical execution sequence while preserving the existing project boundaries:

- LSTM remains the main sequence model
- Word2Vec remains the default embedding model
- FastText remains experimental only
- The UI remains read-only observability / investigation only
- Existing pipeline modes remain available as fallback
- Docker Compose remains the target environment
- No large architectural redesign is allowed during implementation

This roadmap is implementation-oriented.  
It is not a replacement for the project specification, the refactor plan, or the UI plan.

---

## 2. Implementation Principles

The implementation must follow these principles throughout all phases:

1. **Do not break the existing working system**
2. **Do not replace stable infrastructure layers**
3. **Introduce the new AI pipeline gradually**
4. **Keep old pipeline paths available during transition**
5. **Preserve test stability**
6. **Implement only within the agreed architecture**
7. **Avoid scope drift**
8. **Complete each phase before moving to the next**

---

## 3. Current Baseline

The current system already includes:

- FastAPI API layer
- Docker Compose environment
- Prometheus monitoring
- Grafana dashboards
- Alerting engine
- CI/CD workflow
- Existing baseline / transformer runtime logic
- Automated tests

These components are considered stable and must remain intact during the AI pipeline refactor.

The main implementation effort is focused on the new AI pipeline and the required read-only UI support.

---

## 4. Roadmap Overview

The implementation is divided into eight phases:

1. Repository Preparation  
2. NLP Embedding Pipeline  
3. Sequence Dataset Pipeline  
4. System Behavior Modeling  
5. Anomaly Detection Engine  
6. Severity Classification  
7. Engine Integration  
8. UI Observability Enablement  

---

## 5. Detailed Phase Plan

### Phase 1 — Repository Preparation

**Objective:**  
Prepare the repository structure for the new AI pipeline without changing the working system behavior.

**Main Tasks:**
- Create the agreed module structure for:
  - `src/preprocessing`
  - `src/dataset`
  - `src/modeling`
  - `src/engine`
- Create class skeletons for:
  - `LogPreprocessor`
  - `LogDataset`
  - `SystemBehaviorModel`
  - `AnomalyDetector`
  - `SeverityClassifier`
  - `ProactiveMonitorEngine`
- Ensure folder naming and import paths match the agreed architecture
- Keep current runtime code active and untouched where possible

**Expected Output:**
- Clean module structure
- Placeholder classes
- No production behavior change yet

**Exit Criteria:**
- Repository structure is aligned with architecture
- No existing functionality is broken
- Existing tests continue to pass

---

### Phase 2 — NLP Embedding Pipeline

**Objective:**  
Implement the text preprocessing and embedding stage for log lines.

**Main Tasks:**
- Build `LogPreprocessor`
- Implement:
  - text cleaning
  - normalization
  - tokenization
  - embedding generation
- Use **Word2Vec** as the default embedding backend
- Add approved preprocessing improvements:
  - better IP normalization
  - better timestamp normalization
  - better ID normalization
  - better service name normalization
  - better error code normalization
- Save embedding artifact:
  - `models/word2vec.model`

**Experimental Side Task:**
- Allow **FastText** only as an optional side experiment
- Do not make FastText the production default
- Treat FastText as a benchmark / future-ready option only

**Expected Output:**
- Working preprocessing layer
- Embedding generation pipeline
- Word2Vec artifact
- Optional FastText benchmark path

**Exit Criteria:**
- Log line → vector flow works
- Word2Vec is stable
- FastText remains experimental only
- No downstream architecture changes introduced

---

### Phase 3 — Sequence Dataset Pipeline

**Objective:**  
Prepare embedded logs as sequence windows for model training.

**Main Tasks:**
- Implement `LogDataset`
- Build sliding-window sequence generation
- Convert embeddings into tensors
- Prepare PyTorch-compatible dataset and batching flow
- Ensure output shape supports LSTM training

**Expected Output:**
- Sequence windows ready for training
- Data pipeline produces batched tensors

**Exit Criteria:**
- Dataset pipeline is stable
- Sequence shapes are valid and consistent
- Ready for LSTM model input

---

### Phase 4 — System Behavior Modeling

**Objective:**  
Implement the sequence model that learns normal behavioral patterns over time.

**Main Tasks:**
- Implement `SystemBehaviorModel`
- Use **LSTM** as the primary sequence model
- Train on prepared sequence windows
- Produce context vectors representing sequence behavior
- Save trained model artifact

**Constraints:**
- Do not replace LSTM with Transformers
- Transformers remain out of the main MVP path

**Expected Output:**
- Working LSTM behavior model
- Context vector generation

**Exit Criteria:**
- LSTM model trains successfully
- Output is suitable for anomaly detection stage
- Architecture remains aligned with agreed design

---

### Phase 5 — Anomaly Detection Engine

**Objective:**  
Implement proactive anomaly detection based on reconstruction error.

**Main Tasks:**
- Implement `AnomalyDetector`
- Use a **Denoising Autoencoder**
- Train on normal behavior sequences
- Produce:
  - latent vector
  - reconstruction error
- Define anomaly threshold logic
- Save anomaly detection artifact

**Approved Upgrade Included:**
- Maintain **fallback strategy**
- Keep the existing pipeline available during migration
- Do not remove existing model paths
- New autoencoder path should be introduced in parallel

**Expected Output:**
- Reconstruction-based anomaly scoring
- Stable anomaly thresholding
- Parallel migration path preserved

**Exit Criteria:**
- Autoencoder produces usable anomaly scores
- Existing fallback paths remain available
- No destructive migration occurs

---

### Phase 6 — Severity Classification

**Objective:**  
Add severity classification on top of anomaly detection output.

**Main Tasks:**
- Implement `SeverityClassifier`
- Build MLP classifier
- Use:
  - latent representation
  - anomaly score
- Predict severity categories:
  - Info
  - Warning
  - Critical
- Save classifier artifact

**Expected Output:**
- Severity prediction layer
- Cleaner alert prioritization logic

**Exit Criteria:**
- Classifier outputs valid severity classes
- Works with anomaly detector outputs
- Ready for engine orchestration

---

### Phase 7 — Engine Integration

**Objective:**  
Connect all AI stages into one runtime orchestration layer.

**Main Tasks:**
- Implement `ProactiveMonitorEngine`
- Connect:
  - preprocessing
  - embedding
  - sequence modeling
  - anomaly detection
  - severity classification
  - alert pipeline
- Rewire runtime flow carefully
- Keep old pipeline modes as fallback
- Introduce new runtime mode safely
- Expose internal pipeline state where needed

**Approved Upgrade Included:**
- Fallback strategy remains active during integration

**Expected Output:**
- Full end-to-end AI pipeline flow
- Parallel-safe runtime integration
- Stable internal orchestration

**Exit Criteria:**
- Full pipeline runs end-to-end
- Existing fallback modes still work
- No regression to stable infrastructure layers

---

### Phase 8 — UI Observability Enablement

**Objective:**  
Enable the required backend support for the approved read-only UI.

**Main Tasks:**
- Add missing endpoints required by the UI:
  - `GET /pipeline/status`
  - `GET /score/history`
  - `GET /alerts/{alert_id}`
  - `GET /ws/alerts`
- Ensure endpoint outputs support:
  - system status
  - live alert feed
  - score timeline
  - pipeline state
  - investigation workflow
- Keep the UI strictly read-only
- Prepare the system for Streamlit-based observability UI

**Constraints:**
- Do not convert the UI into an admin/control panel
- Do not add write/configuration endpoints
- Keep the UI as observability + investigation only

**Expected Output:**
- UI-required API support
- Backend readiness for dashboard work

**Exit Criteria:**
- Required UI endpoints exist
- UI architecture remains aligned
- Read-only boundary is preserved

---

## 6. Deferred Items

The following items are intentionally deferred and are **not part of the immediate implementation scope**:

- Real-server hardening with reverse proxy
- HTTPS setup
- Public deployment preparation
- Kubernetes deployment
- Transformer-based main sequence architecture
- Doc2Vec integration
- Large-scale infrastructure redesign
- UI control/admin capabilities

These items may be reviewed later after the core AI pipeline is stable.

---

## 7. Experimental Items

The following items are allowed only as controlled experiments:

### FastText Benchmark
FastText may be explored as a side experiment after the Word2Vec pipeline is working.

**Rules:**
- It must not replace Word2Vec by default
- It must not change the agreed architecture
- It must not delay the main implementation path
- Any promotion to default requires clear comparative evidence

---

## 8. Non-Negotiable Constraints

The following rules must remain true throughout implementation:

- LSTM remains the main sequence model
- Word2Vec remains the default embedding model
- FastText remains experimental only
- Existing fallback models remain available during migration
- UI remains read-only
- Docker Compose remains the deployment environment
- Existing stable API / monitoring / alerting / CI layers are not rewritten during the AI refactor
- New work must not break the current repository baseline

---

## 9. Recommended Execution Order

Implementation should proceed in this order:

1. Repository Preparation  
2. NLP Embedding Pipeline  
3. Sequence Dataset Pipeline  
4. LSTM Behavior Model  
5. Autoencoder Anomaly Detection  
6. Severity Classification  
7. Engine Integration  
8. UI Endpoint Enablement  

Only after these phases are stable should the team consider:

9. UI implementation completion  
10. Deployment hardening  
11. Optional production improvements  

---

## 10. Final Implementation Guidance

The safest implementation strategy is:

- keep the architecture fixed
- build incrementally
- preserve the old system during migration
- avoid introducing heavy new ideas mid-way
- finish the AI pipeline before expanding deployment complexity

The project should move forward through controlled phase execution, not through parallel uncontrolled experimentation.

This roadmap is the agreed implementation path unless a future architecture review explicitly approves a change.

---