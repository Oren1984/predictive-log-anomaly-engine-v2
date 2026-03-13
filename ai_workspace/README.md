# AI Workspace

This directory contains the core implementation of the **Predictive Log Anomaly Engine**.

It includes the full pipeline from raw log ingestion to anomaly detection, alerting, and system observability.

The workspace is organized into modular stages that represent the system pipeline.

---

## Directory Structure

### docker
Container definitions and runtime configuration.

### logs
Runtime log outputs generated during system execution.

### monitoring
Monitoring configuration including Prometheus and Grafana dashboards.

### prompts
AI prompts and automation instructions used during development.

### reports
System evaluation reports and experiment outputs.

### stage_21_sampling
Data sampling and dataset preparation utilities.

### stage_22_template_mining
Log template extraction and tokenization.

### stage_23_sequence_builder
Sequence generation from tokenized events.

### stage_24_baseline_model
Baseline anomaly detection model implementation.

### stage_25_evaluation
Model evaluation and performance analysis.

### stage_26_hdfs_supervised
Supervised anomaly detection experiments using HDFS dataset.

### system_design
Original system architecture documentation and planning materials.

### system_audit
System validation reports including architecture review and operational readiness.

---

## Purpose of This Workspace

The goal of this workspace is to provide a **structured AI engineering environment** where each system component is implemented as an isolated stage.

This design allows:

- reproducible experiments
- modular system development
- clear traceability between data processing, modeling, and runtime inference.

---

## Relation to the Overall Project

This directory represents the **core AI engine** of the project.

Additional project components exist at the repository root level, including:

- system documentation
- demonstration notebook
- CI/CD configuration
- container orchestration