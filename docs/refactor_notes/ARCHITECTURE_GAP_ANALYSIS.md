# Predictive Log Anomaly Engine v2
## Architecture Gap Analysis

This document describes the gap between the **current production system** and the **target architecture** planned for v2.

The goal is to clearly understand what exists today, what exists but is not connected, and what must be implemented.

---

# 1. Current Production Architecture (v1)

The existing system is fully operational and includes:

Pipeline:

Logs
→ Regex Template Mining
→ Tokenization
→ Sequence Buffer (rolling windows)
→ ML Scoring
    - IsolationForest baseline
    - Transformer next-token model
    - Ensemble scoring
→ Rule-based Severity Classification
→ Alert Manager
→ FastAPI API
→ Prometheus Metrics
→ Grafana Monitoring
→ Static UI

Main characteristics:

- production-ready
- containerized
- CI/CD enabled
- 500+ tests passing
- real trained artifacts

Active models:

IsolationForest  
Transformer next-token predictor  

Severity logic:

Rule-based thresholds.

---

# 2. Target Architecture (v2)

The specification documents define a different ML pipeline:

Logs
→ LogPreprocessor (Word2Vec / FastText)
→ SystemBehaviorModel (LSTM)
→ AnomalyDetector (Autoencoder)
→ SeverityClassifier (MLP)
→ Alert Manager
→ API
→ Observability
→ UI

Goals of v2:

- semantic log embedding
- temporal behavior modeling
- reconstruction-based anomaly detection
- ML-based severity prediction
- modular ML pipeline

---

# 3. Existing But Unwired Modules

The repository already contains implementations of the target architecture modules.

These exist but are not connected to the runtime.

Modules discovered:

LogPreprocessor  
SystemBehaviorModel  
AnomalyDetector  
SeverityClassifier

Current status:

| Module      | Exists | Wired to runtime |
|------|------|------|
| LogPreprocessor | Yes | No |
| SystemBehaviorModel | Yes | No |
| AnomalyDetector | Yes | No |
| SeverityClassifier | Yes | No |

These modules currently behave as **experimental code only**.

---

# 4. Missing Components

To implement the v2 pipeline, the following elements are missing:

Training pipelines

Word2Vec / FastText training
LSTM training
Autoencoder training
Severity classifier training

Model artifacts

trained embeddings
trained LSTM model
trained Autoencoder
trained MLP classifier

Data pipeline

log preprocessing
embedding generation
sequence dataset

Dependencies

gensim
additional PyTorch utilities

Runtime integration

integration inside inference engine
API integration
alert pipeline integration

---

# 5. Refactor Strategy

The v2 implementation will **not modify the v1 production pipeline**.

Instead:

A **parallel architecture** will be implemented inside the v2 repository.

Steps:

1. integrate existing modules
2. implement missing training pipelines
3. produce trained artifacts
4. build new inference pipeline
5. expose API endpoints
6. validate results
7. promote to production when stable

---

# 6. Principles

The refactor must follow these rules:

1. Do not break the working system logic.
2. Maintain clear module boundaries.
3. Separate training code from inference code.
4. All models must produce reproducible artifacts.
5. The ML pipeline must remain fully modular.