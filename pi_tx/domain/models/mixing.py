"""
Mixing-related classes for RC model configuration.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DifferentialMix:
    """
    Differential steering/mixing between two channels.

    Combines two channels to create differential control, commonly used for
    tank steering where left/right channels are mixed to provide
    forward/turn control.
    """

    left_channel: str  # Channel name
    right_channel: str  # Channel name
    inverse: bool = False  # Swap left/right after mixing

    def __post_init__(self):
        """Validate differential mix configuration."""
        if not self.left_channel or not isinstance(self.left_channel, str):
            raise ValueError(
                f"left_channel must be a non-empty string, got {self.left_channel!r}"
            )
        if not self.right_channel or not isinstance(self.right_channel, str):
            raise ValueError(
                f"right_channel must be a non-empty string, got {self.right_channel!r}"
            )
        if self.left_channel == self.right_channel:
            raise ValueError(
                f"left_channel and right_channel cannot be the same: {self.left_channel}"
            )


@dataclass
class AggregateSource:
    """
    Single source channel for aggregate mixing.

    Represents one input to an aggregate mix with its associated weight.
    """

    channel_name: str
    weight: float = 1.0  # 0.0 to 1.0

    def __post_init__(self):
        """Validate aggregate source configuration."""
        if not self.channel_name or not isinstance(self.channel_name, str):
            raise ValueError(
                f"channel_name must be a non-empty string, got {self.channel_name!r}"
            )
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError(f"weight must be in range [0.0, 1.0], got {self.weight}")


@dataclass
class AggregateMix:
    """
    Aggregate multiple channels into a single output.

    Combines the absolute values of multiple source channels (weighted)
    into a single target channel. Useful for creating virtual channels
    like audio mixing based on control activity.
    """

    sources: List[AggregateSource]
    target_channel: Optional[str] = None  # None = use first source

    def __post_init__(self):
        """Validate aggregate mix configuration."""
        if not self.sources:
            raise ValueError("AggregateMix must have at least one source")
        if self.target_channel is not None and (
            not self.target_channel or not isinstance(self.target_channel, str)
        ):
            raise ValueError(
                f"target_channel must be a non-empty string or None, got {self.target_channel!r}"
            )
