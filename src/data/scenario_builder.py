# src/data/scenario_builder.py

# Purpose: Re-export the ScenarioBuilder class from the src.synthetic.scenario_builder module,
# allowing it to be imported from the data package instead of the synthetic package. 
# This provides a more convenient and consistent import path for users of the ScenarioBuilder class.

# Input: This file does not take any input directly, 
# but it imports the ScenarioBuilder class from the src.synthetic.scenario_builder module. 
# The ScenarioBuilder class is responsible for defining 
# and building scenarios for synthetic log generation,

# Output: This file allows users to import the ScenarioBuilder class from the data package,
# providing a more convenient and consistent import path.
# For example, users can import ScenarioBuilder using:
# from src.data import ScenarioBuilder
# instead of: from src.synthetic.scenario_builder import ScenarioBuilder

# Used by: This file re-exports the ScenarioBuilder class from the src.synthetic.scenario_builder module.
# This allows other modules to import ScenarioBuilder from the data package instead of the synthetic package,
# providing a more convenient and consistent import path for users of the ScenarioBuilder class.

"""
src.data.scenario_builder — Scenario definition builder (re-exported).

Re-exports ScenarioBuilder from src.synthetic.scenario_builder so that
both import paths (src.data and src.synthetic) work interchangeably.
"""
from src.synthetic.scenario_builder import ScenarioBuilder  # noqa: F401

__all__ = ["ScenarioBuilder"]
