# src/modeling/behavior/lstm_model.py
# v2 — Behavior sub-package adapter.
#
# Re-exports SystemBehaviorModel and BehaviorModelConfig from their canonical
# location (src/modeling/behavior_model.py) under the v2 module path so
# training scripts and the v2 pipeline import from a stable, plan-aligned
# location without duplicating code.

from __future__ import annotations

from ..behavior_model import BehaviorModelConfig, SystemBehaviorModel

__all__ = ["BehaviorModelConfig", "SystemBehaviorModel"]
