"""
Example: Creating a model using the new strongly-typed Python classes.

This demonstrates how the cat_d6t model would look when written as Python
code instead of JSON.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import pi_tx
sys.path.insert(0, str(Path(__file__).parent.parent))

from pi_tx.domain import (
    Model,
    ModelIcon,
    Value,
    Endpoint,
    Channels,
    DifferentialMix,
    AggregateMix,
    AggregateSource,
    VirtualControl,
)
from pi_tx.domain.stick_mapping import (
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
    icon=ModelIcon.BULLDOZER,
    values=[
        Value(
            name="left_track",
            control=left_stick.axes.stick_y,
            endpoint=Endpoint(-0.7, 0.7),
        ),
        Value(
            name="right_track",
            control=left_stick.axes.stick_x,
            endpoint=Endpoint(-0.7, 0.7),
            reversed=True,
        ),
        Value(
            name="left_cylinder",
            control=right_stick.axes.stick_y,
            reversed=True,
        ),
        Value(
            name="right_cylinder",
            control=right_stick.axes.stick_x,
        ),
        Value(
            name="ripper",
            control=left_stick.axes.hat_y,
            reversed=True,
        ),
        Value(
            name="lights_cylinders",
            control=left_stick.buttons.sb_2,
            latching=True,
        ),
        Value(
            name="lights_roof",
            control=left_stick.buttons.sb_2,
            latching=True,
        ),
        Value(
            name="sound",
            control=virtual_sound_mix,
        ),
    ],
    channels=Channels(
        ch_1="left_track",
        ch_2="right_track",
        ch_3="left_cylinder",
        ch_4="right_cylinder",
        ch_5="ripper",
        ch_6="lights_cylinders",
        ch_7="lights_roof",
        ch_10="sound",
    ),
    mixes=[
        DifferentialMix(
            left_channel="left_track",
            right_channel="right_track",
            inverse=True,
        ),
        DifferentialMix(
            left_channel="left_cylinder",
            right_channel="right_cylinder",
            inverse=False,
        ),
        AggregateMix(
            sources=[
                AggregateSource(channel_name="left_track", weight=0.3),
                AggregateSource(channel_name="right_track", weight=0.3),
                AggregateSource(channel_name="left_cylinder", weight=0.4),
                AggregateSource(channel_name="right_cylinder", weight=0.4),
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
    print(f"Values: {len(cat_d6t.values)}")

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
    print("Values:")
    for val in cat_d6t.values:
        print(f"  {val.name}: {val.control.name} ({val.control.control_type.value})")
        if val.reversed:
            print(f"       Reversed: Yes")
