# src/data/synth_patterns.py

# Purpose: Re-export all FailurePattern implementations from the src.synthetic.patterns module, 
# allowing them to be imported from the data package instead of the synthetic package. 
# This provides a more convenient and consistent import path for users of the FailurePattern classes.

# Input: This file does not take any input directly, but it imports all FailurePattern implementations 
# from the src.synthetic.patterns module. The FailurePattern classes represent different types 
# of failure patterns that can be used in synthetic log generation scenarios.

# Output: This file re-exports all FailurePattern implementations from the src.synthetic.patterns module, 
# allowing them to be imported from the data package instead of the synthetic package.

# Used by: This file re-exports all FailurePattern implementations from the src.synthetic.patterns module, 
# allowing them to be imported from the data package instead of the synthetic package. 
# This provides a more convenient and consistent import path for users of the FailurePattern classes. 
# For example, users can import the FailurePattern classes using:
# from src.data import FailurePattern, MemoryLeakPattern, DiskFullPattern, AuthBruteForcePattern, NetworkFlapPattern
# instead of: from src.synthetic.patterns import FailurePattern, 
# MemoryLeakPattern, DiskFullPattern, AuthBruteForcePattern, NetworkFlapPattern

"""
src.data.synth_patterns — Failure pattern definitions (re-exported).

This module re-exports all FailurePattern implementations from
src.synthetic.patterns so that code importing from src.data works alongside
code that imports from src.synthetic.
"""
from src.synthetic.patterns import (  # noqa: F401
    AuthBruteForcePattern,
    DiskFullPattern,
    FailurePattern,
    MemoryLeakPattern,
    NetworkFlapPattern,
)

__all__ = [
    "FailurePattern",
    "MemoryLeakPattern",
    "DiskFullPattern",
    "AuthBruteForcePattern",
    "NetworkFlapPattern",
]
