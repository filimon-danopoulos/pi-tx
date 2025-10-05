"""
Value-related classes for RC model configuration.
"""

from dataclasses import dataclass, field
from typing import Union, Optional

from pi_tx.domain.stick_mapping import AxisControl, ButtonControl
from pi_tx.domain.virtual_control import VirtualControl


@dataclass
class Endpoint:
    """
    Represents the output range limits for a value.

    Endpoints define the minimum and maximum output values for a value,
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
class Value:
    """
    Represents a single RC value configuration.

    A value maps an input control (joystick axis, button, etc.) to an
    output value with associated processing parameters.
    """

    name: str  # Value name (e.g., "throttle", "steering", "ch1")
    control: Union[AxisControl, ButtonControl, VirtualControl]

    # Processing parameters (per-value)
    reversed: bool = False
    latching: bool = False
    endpoint: Optional[Endpoint] = None

    def __post_init__(self):
        """Validate value configuration on creation."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError(
                f"Value name must be a non-empty string, got {self.name!r}"
            )

        # Create default endpoint if not provided
        if self.endpoint is None:
            self.endpoint = Endpoint(min=-1.0, max=1.0)

        # Initialize latching state
        self._latch_state: float = 0.0
        self._last_input: float = 0.0

    def preProcess(self, value: float) -> float:
        # Apply latching if enabled
        if self.latching:
            # Detect rising edge: transition from zero to non-zero
            if self._last_input == 0.0 and value != 0.0:
                # Toggle the latch state
                self._latch_state = 1.0 if self._latch_state == 0.0 else 0.0

            # Update last input for next comparison
            self._last_input = value

            # Use the latched state as the value
            value = self._latch_state

        return value

    def postProcess(self, value: float) -> float:
        # Apply reversing
        if self.reversed:
            if self.control.control_type.value == "bipolar":
                value = -value
            else:
                value = 1.0 - value

        # Apply endpoints
        value = self.endpoint.clamp(value)

        return value
