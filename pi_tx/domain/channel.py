"""Base classes for model channels.

Channels represent input controls (sticks, buttons, etc.) that map to
model channel outputs.
"""
from __future__ import annotations

from abc import ABC
from typing import Optional
from dataclasses import dataclass


@dataclass
class Channel(ABC):
    """Base class for a model channel.
    
    A channel represents a single control input that produces a value
    for transmission to the receiver.
    
    Attributes:
        channel_id: The channel number (1-based)
        device_path: Path to the input device (empty for virtual channels)
        control_code: Code identifying the specific control on the device
        device_name: Human-readable name of the input device
        control_name: Human-readable name of the control
    """
    channel_id: int
    device_path: str = ""
    control_code: str = "virtual"
    device_name: str = ""
    control_name: str = ""
    
    def get_control_type(self) -> str:
        """Return the control type identifier for this channel.
        
        This is used by the channel_store to determine how to process values.
        """
        return "unipolar"
    
    def to_dict(self) -> dict:
        """Convert channel configuration to dictionary format.
        
        Returns a dictionary suitable for inclusion in Model.channels.
        """
        result = {
            "control_type": self.get_control_type(),
            "device_path": self.device_path,
            "control_code": self.control_code,
        }
        if self.device_name:
            result["device_name"] = self.device_name
        if self.control_name:
            result["control_name"] = self.control_name
        return result


class BipolarChannel(Channel):
    """A bipolar channel with values ranging from -1.0 to 1.0.
    
    Typical use: joystick axes, analog sticks.
    """
    
    def get_control_type(self) -> str:
        return "bipolar"


class UnipolarChannel(Channel):
    """A unipolar channel with values ranging from 0.0 to 1.0.
    
    Typical use: throttles, sliders, potentiometers.
    """
    
    def get_control_type(self) -> str:
        return "unipolar"


class ButtonChannel(Channel):
    """A momentary button channel (0.0 when released, 1.0 when pressed).
    
    The value returns to 0.0 as soon as the button is released.
    """
    
    def get_control_type(self) -> str:
        return "button"


class LatchingButtonChannel(Channel):
    """A latching button channel that toggles between 0.0 and 1.0.
    
    Each button press toggles the state. The value persists after release.
    """
    
    def get_control_type(self) -> str:
        return "latching-button"


class VirtualChannel(Channel):
    """A virtual channel not tied to physical input.
    
    Virtual channels can be used for computed values (like aggregates)
    or for channels that will be set programmatically.
    """
    
    def __init__(
        self,
        channel_id: int,
        control_name: str = "virtual",
        control_type: str = "unipolar"
    ):
        super().__init__(
            channel_id=channel_id,
            device_path="",
            control_code="virtual",
            device_name="virtual",
            control_name=control_name
        )
        self._control_type = control_type
    
    def get_control_type(self) -> str:
        return self._control_type
