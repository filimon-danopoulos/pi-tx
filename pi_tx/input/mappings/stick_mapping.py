"""
Static stick mapping using Python classes.

This provides a type-safe, autocomplete-friendly way to access stick controls.
Usage: left_stick.axes.stick_y, left_stick.buttons.trigger, etc.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class EventType(Enum):
    """Linux input event types."""

    KEY = 1  # Button/key events
    ABS = 3  # Absolute axis events


class ControlType(Enum):
    """Types of controls."""

    BIPOLAR = "bipolar"
    UNIPOLAR = "unipolar"
    BUTTON = "button"


@dataclass
class Control:
    """Base class for all controls with collection reference support."""

    event_code: int
    event_type: EventType
    name: str
    control_type: ControlType
    collection: Optional["ControlCollection"] = None

    @property
    def device_path(self) -> Optional[str]:
        """Get the device path via collection.stick.device_path."""
        if self.collection is not None and hasattr(self.collection, "stick"):
            stick = self.collection.stick
            if stick is not None and hasattr(stick, "device_path"):
                return stick.device_path
        return None


@dataclass
class AxisControl(Control):
    """Represents an analog axis control."""

    min_value: int = 0
    max_value: int = 16383
    fuzz: int = 63
    flat: int = 1023

    def normalize(self, raw_value: int) -> float:
        """
        Normalize raw hardware value to -1.0..1.0 (bipolar) or 0.0..1.0 (unipolar).

        Args:
            raw_value: Raw value from hardware

        Returns:
            Normalized value
        """
        # Clamp to min/max
        value = max(self.min_value, min(self.max_value, raw_value))

        # Normalize to 0.0 to 1.0
        range_size = self.max_value - self.min_value
        if range_size == 0:
            normalized = 0.0
        else:
            normalized = (value - self.min_value) / range_size

        # Apply deadzone (flat)
        center = 0.5
        deadzone = self.flat / range_size if range_size > 0 else 0.0

        if abs(normalized - center) < deadzone:
            normalized = center

        # Convert to appropriate range
        if self.control_type == ControlType.BIPOLAR:
            # Convert 0..1 to -1..1
            return normalized * 2.0 - 1.0
        else:
            # Keep as 0..1
            return normalized


@dataclass
class ButtonControl(Control):
    """Represents a digital button control."""

    pass  # Inherits all fields from Control


# ============================================================================
# Collection classes that hold controls and stick references
# ============================================================================


class ControlCollection:
    """Base class for axes/buttons collections."""

    def __init__(self, stick=None):
        self.stick = stick
        # Inject collection reference into all control attributes
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                attr = getattr(self, attr_name)
                if isinstance(attr, Control):
                    # Create a copy with collection set
                    attr.collection = self
                    object.__setattr__(self, attr_name, attr)


# ============================================================================
# Left Stick (Thrustmaster T.16000M)
# ============================================================================


class LeftStickAxes(ControlCollection):
    """Axis controls for the left joystick."""

    stick_y = AxisControl(
        event_code=1,
        event_type=EventType.ABS,
        name="stick-y",
        control_type=ControlType.BIPOLAR,
        min_value=0,
        max_value=16383,
        fuzz=63,
        flat=1023,
    )

    stick_x = AxisControl(
        event_code=0,
        event_type=EventType.ABS,
        name="stick-x",
        control_type=ControlType.BIPOLAR,
        min_value=0,
        max_value=16383,
        fuzz=63,
        flat=1023,
    )

    stick_z = AxisControl(
        event_code=5,
        event_type=EventType.ABS,
        name="stick-z",
        control_type=ControlType.BIPOLAR,
        min_value=0,
        max_value=255,
        fuzz=0,
        flat=15,
    )

    hat_y = AxisControl(
        event_code=17,
        event_type=EventType.ABS,
        name="hat-y",
        control_type=ControlType.BIPOLAR,
        min_value=-1,
        max_value=1,
        fuzz=0,
        flat=0,
    )

    hat_x = AxisControl(
        event_code=16,
        event_type=EventType.ABS,
        name="hat-x",
        control_type=ControlType.BIPOLAR,
        min_value=-1,
        max_value=1,
        fuzz=0,
        flat=0,
    )

    throttle = AxisControl(
        event_code=6,
        event_type=EventType.ABS,
        name="throttle",
        control_type=ControlType.UNIPOLAR,
        min_value=0,
        max_value=255,
        fuzz=0,
        flat=15,
    )


class LeftStickButtons(ControlCollection):
    """Button controls for the left joystick."""

    trigger = ButtonControl(
        event_code=288,
        event_type=EventType.KEY,
        name="trigger",
        control_type=ControlType.BUTTON,
    )

    sb_1 = ButtonControl(
        event_code=290,
        event_type=EventType.KEY,
        name="sb-1",
        control_type=ControlType.BUTTON,
    )

    sb_2 = ButtonControl(
        event_code=289,
        event_type=EventType.KEY,
        name="sb-2",
        control_type=ControlType.BUTTON,
    )

    sb_3 = ButtonControl(
        event_code=291,
        event_type=EventType.KEY,
        name="sb-3",
        control_type=ControlType.BUTTON,
    )

    lb_1 = ButtonControl(
        event_code=298,
        event_type=EventType.KEY,
        name="lb-1",
        control_type=ControlType.BUTTON,
    )

    lb_2 = ButtonControl(
        event_code=299,
        event_type=EventType.KEY,
        name="lb-2",
        control_type=ControlType.BUTTON,
    )

    lb_3 = ButtonControl(
        event_code=300,
        event_type=EventType.KEY,
        name="lb-3",
        control_type=ControlType.BUTTON,
    )

    lb_4 = ButtonControl(
        event_code=303,
        event_type=EventType.KEY,
        name="lb-4",
        control_type=ControlType.BUTTON,
    )

    lb_5 = ButtonControl(
        event_code=302,
        event_type=EventType.KEY,
        name="lb-5",
        control_type=ControlType.BUTTON,
    )

    lb_6 = ButtonControl(
        event_code=301,
        event_type=EventType.KEY,
        name="lb-6",
        control_type=ControlType.BUTTON,
    )

    rb_1 = ButtonControl(
        event_code=294,
        event_type=EventType.KEY,
        name="rb-1",
        control_type=ControlType.BUTTON,
    )

    rb_2 = ButtonControl(
        event_code=293,
        event_type=EventType.KEY,
        name="rb-2",
        control_type=ControlType.BUTTON,
    )

    rb_3 = ButtonControl(
        event_code=292,
        event_type=EventType.KEY,
        name="rb-3",
        control_type=ControlType.BUTTON,
    )

    rb_4 = ButtonControl(
        event_code=295,
        event_type=EventType.KEY,
        name="rb-4",
        control_type=ControlType.BUTTON,
    )

    rb_5 = ButtonControl(
        event_code=296,
        event_type=EventType.KEY,
        name="rb-5",
        control_type=ControlType.BUTTON,
    )

    rb_6 = ButtonControl(
        event_code=297,
        event_type=EventType.KEY,
        name="rb-6",
        control_type=ControlType.BUTTON,
    )


class LeftStick:
    """Left Thrustmaster T.16000M joystick."""

    def __init__(self):
        self.device_path = (
            "/dev/input/by-path/pci-0000:00:14.0-usb-0:2:1.0-event-joystick"
        )
        self.name = "Left Joystick"
        self.axes = LeftStickAxes(stick=self)
        self.buttons = LeftStickButtons(stick=self)


# ============================================================================
# Right Stick (Thrustmaster T.16000M)
# ============================================================================


class RightStickAxes(ControlCollection):
    """Axis controls for the right joystick."""

    stick_y = AxisControl(
        event_code=1,
        event_type=EventType.ABS,
        name="stick-y",
        control_type=ControlType.BIPOLAR,
        min_value=0,
        max_value=16383,
        fuzz=63,
        flat=1023,
    )

    stick_x = AxisControl(
        event_code=0,
        event_type=EventType.ABS,
        name="stick-x",
        control_type=ControlType.BIPOLAR,
        min_value=0,
        max_value=16383,
        fuzz=63,
        flat=1023,
    )

    stick_z = AxisControl(
        event_code=5,
        event_type=EventType.ABS,
        name="stick-z",
        control_type=ControlType.BIPOLAR,
        min_value=0,
        max_value=255,
        fuzz=0,
        flat=15,
    )

    hat_y = AxisControl(
        event_code=17,
        event_type=EventType.ABS,
        name="hat-y",
        control_type=ControlType.BIPOLAR,
        min_value=-1,
        max_value=1,
        fuzz=0,
        flat=0,
    )

    hat_x = AxisControl(
        event_code=16,
        event_type=EventType.ABS,
        name="hat-x",
        control_type=ControlType.BIPOLAR,
        min_value=-1,
        max_value=1,
        fuzz=0,
        flat=0,
    )

    throttle = AxisControl(
        event_code=6,
        event_type=EventType.ABS,
        name="throttle",
        control_type=ControlType.UNIPOLAR,
        min_value=0,
        max_value=255,
        fuzz=0,
        flat=15,
    )


class RightStickButtons(ControlCollection):
    """Button controls for the right joystick."""

    trigger = ButtonControl(
        event_code=288,
        event_type=EventType.KEY,
        name="trigger",
        control_type=ControlType.BUTTON,
    )

    sb_1 = ButtonControl(
        event_code=290,
        event_type=EventType.KEY,
        name="sb-1",
        control_type=ControlType.BUTTON,
    )

    sb_2 = ButtonControl(
        event_code=289,
        event_type=EventType.KEY,
        name="sb-2",
        control_type=ControlType.BUTTON,
    )

    sb_3 = ButtonControl(
        event_code=291,
        event_type=EventType.KEY,
        name="sb-3",
        control_type=ControlType.BUTTON,
    )

    lb_1 = ButtonControl(
        event_code=298,
        event_type=EventType.KEY,
        name="lb-1",
        control_type=ControlType.BUTTON,
    )

    lb_2 = ButtonControl(
        event_code=299,
        event_type=EventType.KEY,
        name="lb-2",
        control_type=ControlType.BUTTON,
    )

    lb_3 = ButtonControl(
        event_code=300,
        event_type=EventType.KEY,
        name="lb-3",
        control_type=ControlType.BUTTON,
    )

    lb_4 = ButtonControl(
        event_code=303,
        event_type=EventType.KEY,
        name="lb-4",
        control_type=ControlType.BUTTON,
    )

    lb_5 = ButtonControl(
        event_code=302,
        event_type=EventType.KEY,
        name="lb-5",
        control_type=ControlType.BUTTON,
    )

    lb_6 = ButtonControl(
        event_code=301,
        event_type=EventType.KEY,
        name="lb-6",
        control_type=ControlType.BUTTON,
    )

    rb_1 = ButtonControl(
        event_code=294,
        event_type=EventType.KEY,
        name="rb-1",
        control_type=ControlType.BUTTON,
    )

    rb_2 = ButtonControl(
        event_code=293,
        event_type=EventType.KEY,
        name="rb-2",
        control_type=ControlType.BUTTON,
    )

    rb_3 = ButtonControl(
        event_code=292,
        event_type=EventType.KEY,
        name="rb-3",
        control_type=ControlType.BUTTON,
    )

    rb_4 = ButtonControl(
        event_code=295,
        event_type=EventType.KEY,
        name="rb-4",
        control_type=ControlType.BUTTON,
    )

    rb_5 = ButtonControl(
        event_code=296,
        event_type=EventType.KEY,
        name="rb-5",
        control_type=ControlType.BUTTON,
    )

    rb_6 = ButtonControl(
        event_code=297,
        event_type=EventType.KEY,
        name="rb-6",
        control_type=ControlType.BUTTON,
    )


class RightStick:
    """Right Thrustmaster T.16000M joystick."""

    def __init__(self):
        self.device_path = (
            "/dev/input/by-path/pci-0000:00:14.0-usb-0:3:1.0-event-joystick"
        )
        self.name = "Right Joystick"
        self.axes = RightStickAxes(stick=self)
        self.buttons = RightStickButtons(stick=self)


# ============================================================================
# Public API
# ============================================================================

# Instantiate the sticks
left_stick = LeftStick()
right_stick = RightStick()


# For command-line testing and demonstration
if __name__ == "__main__":
    print("Stick Mapping - Static Python Classes")
    print("=" * 60)
    print()

    # Demonstrate usage
    print("Left Stick:")
    print(f"  Device: {left_stick.name}")
    print(f"  Path: {left_stick.device_path}")
    print()
    print("  Axes:")
    print(
        f"    stick_y: {left_stick.axes.stick_y.name} (code {left_stick.axes.stick_y.event_code})"
    )
    print(
        f"    stick_x: {left_stick.axes.stick_x.name} (code {left_stick.axes.stick_x.event_code})"
    )
    print(
        f"    throttle: {left_stick.axes.throttle.name} (code {left_stick.axes.throttle.event_code})"
    )
    print()
    print("  Buttons:")
    print(
        f"    trigger: {left_stick.buttons.trigger.name} (code {left_stick.buttons.trigger.event_code})"
    )
    print(
        f"    sb_2: {left_stick.buttons.sb_2.name} (code {left_stick.buttons.sb_2.event_code})"
    )
    print()

    print("Right Stick:")
    print(f"  Device: {right_stick.name}")
    print(f"  Path: {right_stick.device_path}")
    print()

    # Demonstrate normalization
    print("Demonstration - Normalizing values:")
    raw_value = 8192  # Middle position
    normalized = left_stick.axes.stick_y.normalize(raw_value)
    print(f"  Raw value {raw_value} -> Normalized: {normalized:.3f}")

    raw_value = 0  # Minimum position
    normalized = left_stick.axes.stick_y.normalize(raw_value)
    print(f"  Raw value {raw_value} -> Normalized: {normalized:.3f}")

    raw_value = 16383  # Maximum position
    normalized = left_stick.axes.stick_y.normalize(raw_value)
    print(f"  Raw value {raw_value} -> Normalized: {normalized:.3f}")

    print()
    print("✓ All controls accessible via dot notation!")
    print("  Example: left_stick.axes.stick_y")
    print("  Example: left_stick.buttons.trigger")
    print("  Example: right_stick.axes.throttle")
