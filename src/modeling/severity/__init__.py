# src/modeling/severity/__init__.py
# v2 severity sub-package — re-exports SeverityClassifier.
from .severity_classifier import (
    SEVERITY_LABELS,
    SeverityClassifier,
    SeverityClassifierConfig,
    SeverityOutput,
)

__all__ = [
    "SeverityClassifierConfig",
    "SeverityClassifier",
    "SeverityOutput",
    "SEVERITY_LABELS",
]
