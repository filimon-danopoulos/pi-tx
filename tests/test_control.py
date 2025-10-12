"""
Test control for use in unit tests.

Provides a simple control implementation that can be used in tests
without requiring actual hardware device paths.
"""

from dataclasses import dataclass
from pi_tx.domain.stick_mapping import Control, ControlType, EventType


@dataclass
class TestControl(Control):
    """
    A simple control for testing purposes.
    
    Unlike real controls (AxisControl, ButtonControl), TestControl doesn't
    require device paths or hardware-specific configuration. It can be used
    to test control type behavior (bipolar vs unipolar) without hardware.
    """
    
    event_code: int = 0
    event_type: EventType = EventType.ABS
    name: str = "test_control"
    control_type: ControlType = ControlType.BIPOLAR
    
    @property
    def device_path(self):
        """TestControl doesn't have a real device path."""
        return None
    
    def normalize(self, raw_value: float) -> float:
        """
        For testing, just return the value as-is since we're working
        with already-normalized test values.
        """
        return raw_value
