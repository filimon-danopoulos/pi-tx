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

    def compute(self, raw_values: dict[str, float]) -> dict[str, float]:
        """
        Compute the differential mix from raw values.

        Args:
            raw_values: Dictionary mapping channel names to values

        Returns:
            Dictionary with the mixed left and right channel values
        """
        # Get current values for both channels
        orig_left = raw_values.get(self.left_channel, 0.0)
        orig_right = raw_values.get(self.right_channel, 0.0)

        # Apply differential mixing (working formula from channel_store)
        left_val = orig_left + orig_right
        right_val = orig_right - orig_left

        # Scale to prevent values from exceeding [-1.0, 1.0] range
        scale = max(1.0, abs(left_val), abs(right_val))

        new_left = left_val / scale
        new_right = right_val / scale

        if self.inverse:
            new_left, new_right = new_right, new_left

        return {
            self.left_channel: new_left,
            self.right_channel: new_right,
        }


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

    def compute(self, raw_values: dict[str, float]) -> dict[str, float]:
        """
        Compute the aggregate mix from raw values.

        Args:
            raw_values: Dictionary mapping channel names to values

        Returns:
            Dictionary with the target channel and its aggregated value
        """
        # Calculate weighted sum of absolute values
        aggregate_value = 0.0
        for src in self.sources:
            src_val = raw_values.get(src.channel_name, 0.0)
            aggregate_value += abs(src_val) * src.weight

        # Clamp to [0.0, 1.0]
        aggregate_value = max(0.0, min(1.0, aggregate_value))

        # Determine target channel
        target = self.target_channel or self.sources[0].channel_name

        return {target: aggregate_value}
