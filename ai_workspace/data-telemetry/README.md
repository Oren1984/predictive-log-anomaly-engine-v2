# Data Lineage & Runtime Telemetry Overview

This document summarizes how data flows through the **Predictive Log Anomaly Engine** and how the system performs during runtime.

The goal is to provide a concise overview of the system's data lifecycle, machine learning pipeline, and runtime performance.

---

# 1. Dataset Overview

The system processes large-scale system logs from two public datasets commonly used in anomaly detection research.

**Sources**

* BGL Supercomputer Logs
* Hadoop Distributed File System (HDFS) Logs

**Scale**

* Raw data size: **~28.5 GB**
* Total events: **15.9 million log records**
* Final merged dataset: **2.6 GB CSV**

These logs represent real-world system activity and serve as the input for the anomaly detection pipeline.

---

# 2. Data Processing Pipeline

The system converts unstructured logs into structured machine-learning features through a multi-stage processing pipeline.

```
Raw Logs
   │
   ▼
Template Mining
   │
   ▼
Session Feature Engineering
   │
   ▼
Anomaly Detection Models
   │
   ▼
Runtime Threshold Calibration
   │
   ▼
Real-time Inference API
```

Pipeline stages:

1. **Template Mining**
   Extracts reusable log templates from raw log messages.

2. **Sequence Building**
   Groups log events by session and generates feature vectors.

3. **Unsupervised Detection**
   Isolation Forest identifies abnormal event sequences.

4. **Supervised Modeling (HDFS)**
   Logistic Regression trained on labeled HDFS sessions.

5. **Runtime Calibration**
   Thresholds calibrated to maintain a target alert rate.

6. **Live Inference Engine**
   Streaming events are processed and scored in real time.

---

# 3. Model Performance

| Dataset   | Model               | F1 Score |
| --------- | ------------------- | -------- |
| BGL Logs  | Isolation Forest    | **0.96** |
| HDFS Logs | Logistic Regression | **0.25** |

The BGL dataset contains clearer anomaly patterns, while HDFS logs present a more imbalanced and complex anomaly detection problem.

---

# 4. Runtime Performance

The inference engine processes streaming log events in real time.

**Performance Metrics**

* Throughput: **~368 events per second**
* Average latency: **27 ms**
* P95 latency: **31 ms**
* Peak memory usage: **461 MB**
* Hardware: **CPU-only deployment**

These metrics demonstrate that the system can operate efficiently without GPU acceleration.

---

# 5. System Architecture

The system is built using a containerized architecture with observability and monitoring.

```
             +----------------------+
             |   Log Event Stream   |
             +----------+-----------+
                        |
                        ▼
               +----------------+
               |  FastAPI API   |
               |   /ingest      |
               +--------+-------+
                        |
                        ▼
            +----------------------+
            |   Inference Engine   |
            |  Feature + Models    |
            +--------+-------------+
                     |
                     ▼
             +--------------+
             | AlertManager |
             +------+-------+
                    |
                    ▼
           +-------------------+
           | Alert Storage/API |
           +-------------------+

Observability Layer
-------------------
Prometheus  → Metrics Collection
Grafana     → Visualization
```

Deployment stack:

* **FastAPI** — real-time inference API
* **Prometheus** — metrics collection
* **Grafana** — monitoring dashboards
* **Docker Compose** — container orchestration

---

# 6. CI/CD and Testing

The project includes automated testing and security validation.

**Testing Summary**

* **233 automated tests**
* Fast test suite + integration tests
* CI pipeline includes:

  * unit tests
  * integration tests
  * security scans

**Security Tools**

* pip-audit
* Trivy container scanning

---

# 7. Key Capabilities

The Predictive Log Anomaly Engine enables proactive monitoring of distributed systems by:

* Learning normal log behavior patterns
* Detecting anomalies in event sequences
* Generating alerts before system failures
* Providing observability dashboards

This architecture demonstrates how machine learning, DevOps practices, and observability tooling can be combined into a production-style anomaly detection system.

---

# 8. Key Project Metrics

| Metric              | Value           |
| ------------------- | --------------- |
| Raw data processed  | 28.5 GB         |
| Log events analyzed | 15.9M           |
| Sessions generated  | 495K            |
| Feature vector size | 407 features    |
| Runtime throughput  | ~368 events/sec |
| Average latency     | 27 ms           |
| Automated tests     | 233             |

---

# 9. Conclusion

The project demonstrates a full lifecycle for AI-driven log anomaly detection:

* Data ingestion and transformation
* Feature engineering and model training
* Real-time anomaly detection
* Observability and monitoring
* Automated testing and CI/CD

The system is designed to be **reproducible, observable, and deployable**, reflecting modern engineering practices for machine learning systems.
