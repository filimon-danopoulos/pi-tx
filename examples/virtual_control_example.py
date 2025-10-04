"""
Example: Using VirtualControl for computed/synthetic channels.

This demonstrates how to create virtual controls for channels that don't
have physical input devices, such as aggregate mixes or computed values.
"""

from pi_tx.domain.models import VirtualControl
from pi_tx.input.mappings.stick_mapping import ControlType


def main():
    print("VirtualControl Usage Example")
    print("=" * 60)
    print()

    # Create virtual controls for different purposes
    print("1. Creating virtual controls:")
    
    # Virtual control for an aggregate mix
    sound_mix = VirtualControl(
        name="sound-mix",
        control_type=ControlType.UNIPOLAR,
    )
    print(f"   {sound_mix.name}: {sound_mix.control_type.value}")
    print(f"   Event code: {sound_mix.event_code} (placeholder)")
    print(f"   Event type: {sound_mix.event_type.name}")
    print()

    # Virtual control for a computed bipolar value
    computed_elevator = VirtualControl(
        name="computed-elevator",
        control_type=ControlType.BIPOLAR,
    )
    print(f"   {computed_elevator.name}: {computed_elevator.control_type.value}")
    print()

    # Virtual control for a button state
    mode_switch = VirtualControl(
        name="mode-switch",
        control_type=ControlType.BUTTON,
    )
    print(f"   {mode_switch.name}: {mode_switch.control_type.value}")
    print()

    print("2. Use cases for VirtualControl:")
    print("   ✓ Aggregate mixes - combine multiple inputs")
    print("   ✓ Differential mixes - computed left/right values")
    print("   ✓ Synthesized channels - calculated from other sources")
    print("   ✓ Mode indicators - derived from button states")
    print("   ✓ Any channel without a physical input device")
    print()

    print("3. Benefits:")
    print("   ✓ Type-safe - same interface as AxisControl/ButtonControl")
    print("   ✓ Simple creation - only name and control_type needed")
    print("   ✓ Self-documenting - clearly identifies virtual channels")
    print("   ✓ Consistent API - works seamlessly with Channel class")


if __name__ == "__main__":
    main()
