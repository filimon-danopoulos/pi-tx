"""
Channel-related classes for RC model configuration.
"""

from dataclasses import dataclass, field
from typing import Union, Optional

from pi_tx.input.mappings.stick_mapping import AxisControl, ButtonControl
from pi_tx.domain.models.virtual_control import VirtualControl


@dataclass
class Endpoint:
    """
    Represents the output range limits for a channel.

    Endpoints define the minimum and maximum output values for a channel,
    allowing fine-tuning of servo travel limits.
    """

    min: float = -1.0
    max: float = 1.0

    def __post_init__(self):
        """Validate endpoint configuration."""
        if self.min >= self.max:
            raise ValueError(
                f"Endpoint min ({self.min}) must be less than max ({self.max})"
            )

    def clamp(self, value: float) -> float:
        """Clamp a value to the endpoint range."""
        return max(self.min, min(self.max, value))


@dataclass
class Channel:
    """
    Represents a single RC channel configuration.

    A channel maps an input control (joystick axis, button, etc.) to an
    output channel with associated processing parameters.
    """

    name: str  # Channel name (e.g., "throttle", "steering", "ch1")
    control: Union[AxisControl, ButtonControl, VirtualControl]

    # Processing parameters (per-channel)
    reversed: bool = False
    latching: bool = False
    endpoint: Optional[Endpoint] = None

    def __post_init__(self):
        """Validate channel configuration on creation."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError(
                f"Channel name must be a non-empty string, got {self.name!r}"
            )

        # Create default endpoint if not provided
        if self.endpoint is None:
            self.endpoint = Endpoint(min=-1.0, max=1.0)

    def postProcess(self, value: float) -> float:
        """
        Apply post-processing to a channel value.

        This applies reversing and endpoint clamping to the value.

        Args:
            value: The input value to process

        Returns:
            The processed value after reversing and endpoint clamping
        """
        # Apply reversing
        if self.reversed:
            if self.control.control_type.value == "bipolar":
                value = -value
            else:
                value = 1.0 - value

        # Apply endpoints
        value = self.endpoint.clamp(value)

        return value
