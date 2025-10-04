"""
Virtual control for channels without physical input devices.
"""

from dataclasses import dataclass

from pi_tx.input.mappings.stick_mapping import EventType, ControlType


@dataclass(frozen=True)
class VirtualControl:
    """
    Represents a virtual control with no physical input device.

    Used for computed channels like aggregate mixes or other synthesized values.
    """

    name: str
    control_type: ControlType

    def __post_init__(self):
        """Set virtual-specific attributes."""
        # Virtual controls use placeholder event values
        object.__setattr__(self, "event_code", 0)
        object.__setattr__(self, "event_type", EventType.ABS)
