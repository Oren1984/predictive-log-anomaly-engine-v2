# Predictive Log Anomaly Engine v2
## Refactor Implementation Plan

This document defines the implementation plan for the v2 architecture.

The goal is to migrate from the current anomaly detection pipeline to the new ML-based architecture defined in the specification.

---

# Phase 1 – Repository Structure

Create a clean modular structure.

Example:

src/

preprocessing/
log_preprocessor.py

modeling/

embeddings/
word2vec_trainer.py

behavior/
lstm_model.py

anomaly/
autoencoder.py

severity/
severity_classifier.py

runtime/

pipeline_v2.py
inference_engine_v2.py

api/

routes_v2.py

training/

train_embeddings.py
train_behavior_model.py
train_autoencoder.py
train_severity_model.py

models/

embeddings/
behavior/
anomaly/
severity/

---

# Phase 2 – Data Pipeline

Implement log preprocessing.

Steps:

1 tokenize logs
2 clean text
3 build vocabulary
4 train embeddings
5 generate embedding vectors

Outputs:

embedding model  
embedding vectors  

---

# Phase 3 – Behavior Modeling

Train the LSTM model.

Input:

embedded sequences

Output:

latent representation of system behavior

---

# Phase 4 – Anomaly Detection

Train the autoencoder.

Goal:

detect abnormal sequences using reconstruction error.

---

# Phase 5 – Severity Prediction

Train the MLP classifier.

Input:

latent representation + anomaly score

Output:

severity class

classes:

info  
warning  
critical  

---

# Phase 6 – Runtime Pipeline

Implement new inference pipeline.

Flow:

Logs
→ Preprocessor
→ Embedding
→ LSTM behavior model
→ Autoencoder anomaly scoring
→ Severity classifier
→ Alert manager

---

# Phase 7 – API Integration

Expose endpoints:

POST /ingest_v2

GET /alerts_v2

GET /health

GET /metrics

---

# Phase 8 – Evaluation

Compare pipelines:

v1 vs v2

Metrics:

precision
recall
F1
latency
false positives

---

# Phase 9 – Deployment

Deploy new pipeline via Docker.

Keep both pipelines available.

Environment flag:

MODEL_MODE=v1  
MODEL_MODE=v2  

---

# Phase 10 – Promotion

When v2 demonstrates stable results:

v2 becomes default runtime pipeline.