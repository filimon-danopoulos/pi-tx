"""
Example demonstrating latching channel functionality.

Latching channels toggle their state on each press (0->1 transition).
This is useful for switches, gear changes, or any on/off functionality
that should toggle with each button press rather than following the
button state.
"""

from pi_tx.domain.models import (
    Model,
    Channel,
    Endpoint,
    VirtualControl,
)
from pi_tx.input.mappings.stick_mapping import ControlType


def demonstrate_latching():
    """Demonstrate basic latching functionality."""
    print("=" * 60)
    print("Latching Channel Example")
    print("=" * 60)
    print()
    
    # Create a model with a latching channel
    button = VirtualControl(name="gear_button", control_type=ControlType.BUTTON)
    model = Model(
        name="latching_demo",
        model_id="demo123",
        channels=[
            Channel(
                name="gear",
                control=button,
                latching=True,  # Enable latching
            ),
        ],
    )
    
    gear_channel = model.get_channel_by_name("gear")
    
    print("Channel: 'gear' with latching=True")
    print()
    print("Simulating button presses:")
    print("-" * 60)
    
    # Simulate button press sequence
    sequence = [
        (0.0, "Initial state (button released)"),
        (1.0, "Button pressed (1st time)"),
        (0.0, "Button released"),
        (1.0, "Button pressed (2nd time)"),
        (0.0, "Button released"),
        (1.0, "Button pressed (3rd time)"),
        (0.0, "Button released"),
    ]
    
    for raw_value, description in sequence:
        # Simulate the input flow: preProcess happens at input stage
        preprocessed = gear_channel.preProcess(raw_value)
        model.raw_values = {"gear": preprocessed}
        result = model.readValues()
        
        print(f"{description:40s} raw={raw_value:.1f} -> output={result['gear']:.1f}")
    
    print()


def demonstrate_latching_with_features():
    """Demonstrate latching combined with reversing and endpoints."""
    print("=" * 60)
    print("Latching with Reversing and Endpoints")
    print("=" * 60)
    print()
    
    button = VirtualControl(name="switch", control_type=ControlType.BUTTON)
    model = Model(
        name="advanced_demo",
        model_id="demo456",
        channels=[
            Channel(
                name="flaps",
                control=button,
                latching=True,
                reversed=True,  # Reverse the output
                endpoint=Endpoint(min=0.2, max=0.8),  # Limit range
            ),
        ],
    )
    
    flaps_channel = model.get_channel_by_name("flaps")
    
    print("Channel: 'flaps'")
    print("  - latching=True (toggles on each press)")
    print("  - reversed=True (inverts output)")
    print("  - endpoint=(0.2, 0.8) (limits range)")
    print()
    print("Processing flow:")
    print("  1. preProcess: applies latching at input stage")
    print("  2. readValues -> _process: applies mixing")
    print("  3. readValues -> _postProcess: applies reversing & endpoints")
    print()
    print("Simulating button presses:")
    print("-" * 60)
    
    sequence = [
        (0.0, "Initial state"),
        (1.0, "1st press (toggle ON)"),
        (0.0, "Release"),
        (1.0, "2nd press (toggle OFF)"),
        (0.0, "Release"),
    ]
    
    for raw_value, description in sequence:
        preprocessed = flaps_channel.preProcess(raw_value)
        model.raw_values = {"flaps": preprocessed}
        result = model.readValues()
        
        print(f"{description:25s} raw={raw_value:.1f} -> "
              f"latched={preprocessed:.1f} -> output={result['flaps']:.1f}")
        
        # Explain the transformation
        if raw_value == 1.0:
            print(f"  └─ Latched={preprocessed:.1f}, "
                  f"Reversed={1.0 - preprocessed:.1f}, "
                  f"Clamped={result['flaps']:.1f}")
    
    print()


def demonstrate_multiple_latching_channels():
    """Demonstrate multiple independent latching channels."""
    print("=" * 60)
    print("Multiple Independent Latching Channels")
    print("=" * 60)
    print()
    
    btn1 = VirtualControl(name="button1", control_type=ControlType.BUTTON)
    btn2 = VirtualControl(name="button2", control_type=ControlType.BUTTON)
    
    model = Model(
        name="multi_demo",
        model_id="demo789",
        channels=[
            Channel(name="gear", control=btn1, latching=True),
            Channel(name="lights", control=btn2, latching=True),
        ],
    )
    
    gear_ch = model.get_channel_by_name("gear")
    lights_ch = model.get_channel_by_name("lights")
    
    print("Two independent latching channels: 'gear' and 'lights'")
    print()
    print("Simulating button presses:")
    print("-" * 60)
    
    # Define button press sequence
    steps = [
        ((0.0, 0.0), "Both buttons released"),
        ((1.0, 0.0), "Press gear button"),
        ((0.0, 0.0), "Release gear button"),
        ((0.0, 1.0), "Press lights button"),
        ((0.0, 0.0), "Release lights button"),
        ((1.0, 0.0), "Press gear button again"),
        ((0.0, 0.0), "Release gear button"),
    ]
    
    for (gear_raw, lights_raw), description in steps:
        gear_pre = gear_ch.preProcess(gear_raw)
        lights_pre = lights_ch.preProcess(lights_raw)
        model.raw_values = {"gear": gear_pre, "lights": lights_pre}
        result = model.readValues()
        
        print(f"{description:30s} gear={result['gear']:.1f}  lights={result['lights']:.1f}")
    
    print()
    print("Note: Each channel maintains independent state!")
    print()


if __name__ == "__main__":
    demonstrate_latching()
    demonstrate_latching_with_features()
    demonstrate_multiple_latching_channels()
    
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    print("Latching channels:")
    print("  • Toggle state on each button press (0→1 transition)")
    print("  • Maintain state when button is released")
    print("  • Applied at input stage (preProcess)")
    print("  • Work independently for each channel")
    print("  • Compatible with reversing, endpoints, and mixing")
    print()
