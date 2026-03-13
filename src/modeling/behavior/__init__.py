# src/modeling/behavior/__init__.py
# v2 behavior sub-package — re-exports SystemBehaviorModel.
from .lstm_model import BehaviorModelConfig, SystemBehaviorModel

__all__ = ["BehaviorModelConfig", "SystemBehaviorModel"]
