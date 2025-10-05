"""
CAT 950M Wheel Loader Model

This model defines the controls for a Caterpillar 950M wheel loader.
The 950M has:
- Drive motor (forward/reverse)
- Steering motor (left/right)
- Bucket lift and tilt with separate motors
- Work lights and beacon
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import pi_tx
sys.path.insert(0, str(Path(__file__).parent.parent))

from pi_tx.domain import (
    Model,
    ModelIcon,
    Channel,
    Endpoint,
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


# Create a virtual control for the aggregate mix output
virtual_sound_mix = VirtualControl(
    name="sound-mix",
    control_type=ControlType.UNIPOLAR,
)

cat_950m = Model(
    name="cat_950m",
    model_id="a3f8c7d9e1f54b2a9856f9e8d7c9f6bc",
    rx_num=2,
    icon=ModelIcon.TRACTOR,
    channels=[
        Channel(name="drive", control=left_stick.axes.stick_y, reversed=True),
        Channel(
            name="steering",
            control=left_stick.axes.stick_x,
            endpoint=Endpoint(-0.7, 0.7),
        ),
        Channel(
            name="bucket_lift",
            control=right_stick.axes.stick_y,
            reversed=True,
        ),
        Channel(
            name="bucket_tilt",
            control=right_stick.axes.stick_z,
        ),
        Channel(
            name="quick_connect", control=right_stick.buttons.trigger, latching=True
        ),
        Channel(
            name="work_lights",
            control=left_stick.buttons.sb_2,
            latching=True,
        ),
        Channel(
            name="beacon",
            control=left_stick.buttons.sb_3,
            latching=True,
        ),
        Channel(
            name="sound",
            control=virtual_sound_mix,
        ),
    ],
    mixes=[
        AggregateMix(
            sources=[
                AggregateSource(channel_name="drive", weight=0.4),
                AggregateSource(channel_name="steering", weight=0.2),
                AggregateSource(channel_name="bucket_lift", weight=0.3),
                AggregateSource(channel_name="bucket_tilt", weight=0.3),
            ],
            target_channel="sound",
        ),
    ],
)


# For command-line testing
if __name__ == "__main__":
    print(f"Model: {cat_950m.name}")
    print(f"Model ID: {cat_950m.model_id}")
    print(f"RX Number: {cat_950m.rx_num}")
    print(f"Channels: {len(cat_950m.channels)}")

    # Count mix types
    differential_count = sum(
        1 for m in cat_950m.mixes if isinstance(m, DifferentialMix)
    )
    aggregate_count = sum(1 for m in cat_950m.mixes if isinstance(m, AggregateMix))
    print(f"Mixes: {len(cat_950m.mixes)} (Aggregate: {aggregate_count})")
    print()

    # Show validation passes
    errors = cat_950m.validate()
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ Model validation passed!")

    print()
    print("Channels:")
    for ch in cat_950m.channels:
        print(f"  {ch.name}: {ch.control.name} ({ch.control.control_type.value})")
        if ch.reversed:
            print(f"       Reversed: Yes")
