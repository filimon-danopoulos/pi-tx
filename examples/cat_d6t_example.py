"""
Example: Creating a model using the new strongly-typed Python classes.

This demonstrates how the cat_d6t model would look when written as Python
code instead of JSON.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import pi_tx
sys.path.insert(0, str(Path(__file__).parent.parent))

from pi_tx.domain.models import (
    Model,
    Channel,
    Endpoint,
    DifferentialMix,
    AggregateMix,
    AggregateSource,
    VirtualControl,
)
from pi_tx.input.mappings.stick_mapping import (
    left_stick,
    right_stick,
    ControlType,
)


# Define the cat_d6t model using Python classes

# Create a virtual control for the aggregate mix output
virtual_sound_mix = VirtualControl(
    name="sound-mix",
    control_type=ControlType.UNIPOLAR,
)

cat_d6t = Model(
    name="cat_d6t",
    model_id="f2f9b6c8c2e44d3d8947e7d6b8c6e5ab",
    rx_num=1,
    channels=[
        Channel(
            name="left_track",
            control=left_stick.axes.stick_y,
            reversed=True,
        ),
        Channel(
            name="right_track",
            control=left_stick.axes.stick_x,
        ),
        Channel(
            name="left_cylinder",
            control=right_stick.axes.stick_y,
            reversed=True,
        ),
        Channel(
            name="right_cylinder",
            control=right_stick.axes.stick_x,
        ),
        Channel(
            name="ripper",
            control=left_stick.axes.hat_y,
            reversed=True,
        ),
        Channel(
            name="lights_cylinders",
            control=left_stick.buttons.sb_2,
            latching=True,
        ),
        Channel(
            name="lights_roof",
            control=left_stick.buttons.sb_2,
            latching=True,
        ),
        Channel(
            name="sound",
            control=virtual_sound_mix,
        ),
    ],
    mixes=[
        DifferentialMix(
            left_channel="right_track",
            right_channel="left_track",
            inverse=True,
        ),
        DifferentialMix(
            left_channel="right_cylinder",
            right_channel="left_cylinder",
            inverse=False,
        ),
        AggregateMix(
            sources=[
                AggregateSource(channel_name="left_track", weight=0.4),
                AggregateSource(channel_name="right_track", weight=0.4),
                AggregateSource(channel_name="left_cylinder", weight=0.2),
                AggregateSource(channel_name="right_cylinder", weight=0.2),
            ],
            target_channel="sound",
        ),
    ],
)


# For command-line testing
if __name__ == "__main__":
    print(f"Model: {cat_d6t.name}")
    print(f"Model ID: {cat_d6t.model_id}")
    print(f"RX Number: {cat_d6t.rx_num}")
    print(f"Channels: {len(cat_d6t.channels)}")

    # Count mix types
    differential_count = sum(1 for m in cat_d6t.mixes if isinstance(m, DifferentialMix))
    aggregate_count = sum(1 for m in cat_d6t.mixes if isinstance(m, AggregateMix))
    print(
        f"Mixes: {len(cat_d6t.mixes)} (Differential: {differential_count}, Aggregate: {aggregate_count})"
    )
    print()

    # Show validation passes
    errors = cat_d6t.validate()
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ Model validation passed!")

    print()
    print("Channels:")
    for ch in cat_d6t.channels:
        print(f"  {ch.name}: {ch.control.name} ({ch.control.control_type.value})")
        if ch.reversed:
            print(f"       Reversed: Yes")
