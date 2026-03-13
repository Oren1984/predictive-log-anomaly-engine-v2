# src/data/synth_generator.py

# Purpose: Re-export the SyntheticLogGenerator class from the src.synthetic.generator module,
# allowing it to be imported from the data package instead of the synthetic package. 
# This provides a more convenient and consistent import path for users of the SyntheticLogGenerator class.

# Input: This file does not take any input directly, 
# but it imports the SyntheticLogGenerator class from the src.synthetic.generator module. 
# The SyntheticLogGenerator class is responsible for generating 
# synthetic log events based on defined scenarios and patterns.

# Output: This file allows users to import the SyntheticLogGenerator class from the data package, 
# providing a more convenient and consistent import path. For example, 
# users can import SyntheticLogGenerator using:
# from src.data import SyntheticLogGenerator

# Used by: This file re-exports the SyntheticLogGenerator class from the src.synthetic.generator module. 
# This allows other modules to import SyntheticLogGenerator from the data package 
# instead of the synthetic package, providing a more convenient 
# and consistent import path for users of the SyntheticLogGenerator class.

"""
src.data.synth_generator — Synthetic log event generator (re-exported).

Re-exports SyntheticLogGenerator from src.synthetic.generator so that
both import paths (src.data and src.synthetic) work interchangeably.
"""
from src.synthetic.generator import SyntheticLogGenerator  # noqa: F401

__all__ = ["SyntheticLogGenerator"]
