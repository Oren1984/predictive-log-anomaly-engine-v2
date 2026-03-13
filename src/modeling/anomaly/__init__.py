# src/modeling/anomaly/__init__.py
# v2 anomaly sub-package — re-exports AnomalyDetector.
from .autoencoder import AEOutput, AnomalyDetector, AnomalyDetectorConfig

__all__ = ["AnomalyDetectorConfig", "AnomalyDetector", "AEOutput"]
