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
            id=1,
            control=left_stick.axes.stick_y,
            reversed=True,
        ),
        Channel(
            id=2,
            control=left_stick.axes.stick_x,
        ),
        Channel(
            id=3,
            control=right_stick.axes.stick_y,
            reversed=True,
        ),
        Channel(
            id=4,
            control=right_stick.axes.stick_x,
        ),
        Channel(
            id=5,
            control=left_stick.axes.hat_y,
            reversed=True,
        ),
        Channel(
            id=6,
            control=left_stick.buttons.sb_2,
            latching=True,
        ),
        Channel(
            id=7,
            control=virtual_sound_mix,
            reversed=True,
        ),
    ],
    mixes=[
        DifferentialMix(
            left_channel=2,
            right_channel=1,
            inverse=True,
        ),
        DifferentialMix(
            left_channel=4,
            right_channel=3,
            inverse=False,
        ),
        AggregateMix(
            sources=[
                AggregateSource(channel_id=1, weight=0.2),
                AggregateSource(channel_id=2, weight=0.2),
                AggregateSource(channel_id=3, weight=0.4),
                AggregateSource(channel_id=4, weight=0.4),
            ],
            target_channel=7,
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
        print(f"  Ch{ch.id}: {ch.control.name} ({ch.control.control_type.value})")
        if ch.reversed:
            print(f"       Reversed: Yes")
