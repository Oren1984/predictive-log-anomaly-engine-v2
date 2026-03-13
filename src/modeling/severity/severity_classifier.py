# src/modeling/severity/severity_classifier.py
# v2 — Severity sub-package adapter.
#
# Re-exports SeverityClassifier, SeverityClassifierConfig, SeverityOutput, and
# SEVERITY_LABELS from their canonical location
# (src/modeling/severity_classifier.py) under the v2 module path so training
# scripts and the v2 pipeline import from a stable, plan-aligned location
# without duplicating code.

from __future__ import annotations

from ..severity_classifier import (
    SEVERITY_LABELS,
    SeverityClassifier,
    SeverityClassifierConfig,
    SeverityOutput,
)

__all__ = [
    "SEVERITY_LABELS",
    "SeverityClassifier",
    "SeverityClassifierConfig",
    "SeverityOutput",
]
