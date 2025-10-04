"""
Strongly-typed model definitions for RC transmitter configuration.

This module provides type-safe classes for defining RC models, replacing
the previous JSON-based configuration approach with Python classes that
provide IDE autocomplete, type checking, and validation.

Classes are organized into separate modules:
- channel: Channel and Endpoint
- virtual_control: VirtualControl for computed/synthetic channels
- mixing: DifferentialMix, AggregateSource, AggregateMix
- model: Model (top-level configuration)

All classes are re-exported here for convenient imports.
"""

# Import all classes from submodules
from .channel import Channel, Endpoint
from .virtual_control import VirtualControl
from .mixing import DifferentialMix, AggregateSource, AggregateMix
from .model import Model

# Export all public classes
__all__ = [
    "Endpoint",
    "Channel",
    "VirtualControl",
    "DifferentialMix",
    "AggregateSource",
    "AggregateMix",
    "Model",
]
