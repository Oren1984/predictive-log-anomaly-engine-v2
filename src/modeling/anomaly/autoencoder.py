# src/modeling/anomaly/autoencoder.py
# v2 — Anomaly sub-package adapter.
#
# Re-exports AnomalyDetector, AnomalyDetectorConfig, and AEOutput from their
# canonical location (src/modeling/anomaly_detector.py) under the v2 module
# path so training scripts and the v2 pipeline import from a stable,
# plan-aligned location without duplicating code.

from __future__ import annotations

from ..anomaly_detector import AEOutput, AnomalyDetector, AnomalyDetectorConfig

__all__ = ["AnomalyDetectorConfig", "AnomalyDetector", "AEOutput"]
