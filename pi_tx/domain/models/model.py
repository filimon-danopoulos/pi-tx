"""
Top-level Model class for RC transmitter configuration.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .channel import Channel
from .mixing import DifferentialMix, AggregateMix


@dataclass
class Model:
    """
    Complete RC model configuration.

    Defines all channels, mixing, and processing for a complete RC model.
    This is the top-level configuration object that gets loaded and used
    by the transmitter system.
    """

    name: str
    model_id: str
    channels: List[Channel]
    differential_mixes: List[DifferentialMix] = field(default_factory=list)
    aggregate_mixes: List[AggregateMix] = field(default_factory=list)
    rx_num: int = 0  # Receiver number (0-15)
    bind_timestamp: str = ""  # ISO timestamp

    def __post_init__(self):
        """Validate model configuration on creation."""
        errors = self.validate()
        if errors:
            raise ValueError(
                f"Invalid model configuration for '{self.name}':\n"
                + "\n".join(f"  - {err}" for err in errors)
            )

    def validate(self) -> List[str]:
        """
        Validate model configuration and return list of errors.

        Returns:
            List of error messages. Empty list means valid configuration.
        """
        errors = []

        # Check for duplicate channel IDs
        channel_ids = [ch.id for ch in self.channels]
        if len(channel_ids) != len(set(channel_ids)):
            duplicates = [cid for cid in channel_ids if channel_ids.count(cid) > 1]
            errors.append(f"Duplicate channel IDs found: {set(duplicates)}")

        # Check channel IDs are positive (already checked in Channel.__post_init__)
        # but we check here for completeness
        if any(ch.id <= 0 for ch in self.channels):
            errors.append("All channel IDs must be positive")

        # Validate mix references
        valid_ids = set(channel_ids)

        for i, mix in enumerate(self.differential_mixes):
            if mix.left_channel not in valid_ids:
                errors.append(
                    f"Differential mix {i}: references invalid channel {mix.left_channel}"
                )
            if mix.right_channel not in valid_ids:
                errors.append(
                    f"Differential mix {i}: references invalid channel {mix.right_channel}"
                )

        for i, mix in enumerate(self.aggregate_mixes):
            for j, src in enumerate(mix.sources):
                if src.channel_id not in valid_ids:
                    errors.append(
                        f"Aggregate mix {i}, source {j}: "
                        f"references invalid channel {src.channel_id}"
                    )
            if mix.target_channel and mix.target_channel not in valid_ids:
                errors.append(
                    f"Aggregate mix {i}: target channel {mix.target_channel} is invalid"
                )

        # Validate rx_num range
        if not (0 <= self.rx_num <= 15):
            errors.append(f"rx_num must be in range [0, 15], got {self.rx_num}")

        return errors

    def get_channel_by_id(self, channel_id: int) -> Optional[Channel]:
        """Get a channel by its ID."""
        for ch in self.channels:
            if ch.id == channel_id:
                return ch
        return None

    def get_channel_by_name(self, control_name: str) -> Optional[Channel]:
        """Get a channel by its control name."""
        for ch in self.channels:
            if ch.control.name == control_name:
                return ch
        return None
