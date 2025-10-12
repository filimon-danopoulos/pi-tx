"""
Strongly-typed model definitions for RC transmitter configuration.

This module provides type-safe classes for defining RC models, replacing
the previous JSON-based configuration approach with Python classes that
provide IDE autocomplete, type checking, and validation.

Classes are organized into separate modules:
- value: Value and Endpoint
- mixing: DifferentialMix, AggregateSource, AggregateMix
- model: Model (top-level configuration)

All classes are re-exported here for convenient imports.
"""

# Import all classes from submodules
from .value import Value, Endpoint
from .mixing import DifferentialMix, AggregateSource, AggregateMix
from .model import Model, ModelIcon, Channels

# Backward compatibility alias
Channel = Value

# Export all public classes
__all__ = [
    "Endpoint",
    "Value",
    "Channel",  # Backward compatibility
    "DifferentialMix",
    "AggregateSource",
    "AggregateMix",
    "Model",
    "ModelIcon",
    "Channels",
]
