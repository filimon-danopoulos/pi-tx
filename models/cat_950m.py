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
    values=[
        Value(name="drive", control=left_stick.axes.stick_y, reversed=True),
        Value(
            name="steering",
            control=left_stick.axes.stick_x,
            endpoint=Endpoint(-0.7, 0.7),
        ),
        Value(
            name="bucket_lift",
            control=right_stick.axes.stick_y,
            reversed=True,
        ),
        Value(
            name="bucket_tilt",
            control=right_stick.axes.stick_z,
        ),
        Value(name="quick_connect", control=right_stick.buttons.trigger, latching=True),
        Value(
            name="work_lights",
            control=left_stick.buttons.sb_2,
            latching=True,
        ),
        Value(
            name="beacon",
            control=left_stick.buttons.sb_3,
            latching=True,
        ),
        Value(
            name="sound",
            control=virtual_sound_mix,
        ),
    ],
    channels=Channels(
        ch_1="drive",
        ch_2="steering",
        ch_3="bucket_lift",
        ch_4="bucket_tilt",
        ch_5="quick_connect",
        ch_6="work_lights",
        ch_7="beacon",
        ch_10="sound",
    ),
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
    print(f"Values: {len(cat_950m.values)}")

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
    print("Values:")
    for val in cat_950m.values:
        print(f"  {val.name}: {val.control.name} ({val.control.control_type.value})")
        if val.reversed:
            print(f"       Reversed: Yes")
    
    print()
    print("Channel Mapping:")
    if cat_950m.channels:
        for i in range(1, 15):
            ch_attr = f"ch_{i}"
            value_name = getattr(cat_950m.channels, ch_attr)
            if value_name:
                print(f"  Channel {i}: {value_name}")
