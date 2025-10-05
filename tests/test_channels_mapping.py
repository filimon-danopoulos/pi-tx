"""
Tests for the Channels mapping and getChannels() method.
"""

import pytest
from pi_tx.domain import (
    Model,
    Channels,
    Value,
    VirtualControl,
)
from pi_tx.domain.stick_mapping import ControlType


class TestChannelsMapping:
    """Test the Channels mapping class and getChannels() method."""

    def test_getchannels_with_sequential_mapping(self):
        """getChannels() with sequential channel mapping."""
        ctrl1 = VirtualControl(name="ctrl1", control_type=ControlType.BIPOLAR)
        ctrl2 = VirtualControl(name="ctrl2", control_type=ControlType.UNIPOLAR)

        model = Model(
            name="test",
            model_id="test123",
            values=[
                Value(name="val1", control=ctrl1),
                Value(name="val2", control=ctrl2),
            ],
            channels=Channels(
                ch_1="val1",
                ch_2="val2",
            ),
        )

        # Set some raw values
        model.raw_values = {"val1": 0.5, "val2": 0.8}

        # Get channels
        channels = model.getChannels()

        # Should return 14 channels
        assert len(channels) == 14

        # First two should have values, rest should be 0.0
        assert channels[0] == 0.5
        assert channels[1] == 0.8
        for i in range(2, 14):
            assert channels[i] == 0.0

    def test_getchannels_with_mapping(self):
        """getChannels() with Channels mapping should map to specific positions."""
        ctrl1 = VirtualControl(name="ctrl1", control_type=ControlType.BIPOLAR)
        ctrl2 = VirtualControl(name="ctrl2", control_type=ControlType.UNIPOLAR)
        ctrl3 = VirtualControl(name="ctrl3", control_type=ControlType.BIPOLAR)

        model = Model(
            name="test",
            model_id="test123",
            values=[
                Value(name="throttle", control=ctrl1),
                Value(name="steering", control=ctrl2),
                Value(name="lights", control=ctrl3),
            ],
            channels=Channels(
                ch_1="throttle",
                ch_3="steering",  # Skip ch_2
                ch_10="lights",  # Skip ch_4-9
            ),
        )

        # Set raw values
        model.raw_values = {"throttle": 0.6, "steering": 0.4, "lights": 1.0}

        # Get channels
        channels = model.getChannels()

        # Check specific mappings
        assert channels[0] == 0.6  # ch_1 = throttle
        assert channels[1] == 0.0  # ch_2 unmapped
        assert channels[2] == 0.4  # ch_3 = steering
        assert channels[9] == 1.0  # ch_10 = lights

        # Check others are 0.0
        for i in [3, 4, 5, 6, 7, 8, 10, 11, 12, 13]:
            assert channels[i] == 0.0

    def test_getchannels_respects_14_channel_limit(self):
        """getChannels() should never return more than 14 channels."""
        # Create model with more than 14 values
        values = []
        channel_dict = {}
        for i in range(20):
            ctrl = VirtualControl(name=f"ctrl{i}", control_type=ControlType.UNIPOLAR)
            values.append(Value(name=f"val{i}", control=ctrl))
            # Only map first 14 to channels
            if i < 14:
                channel_dict[f"ch_{i+1}"] = f"val{i}"
        
        model = Model(
            name="test",
            model_id="test123",
            values=values,
            channels=Channels(**channel_dict),
        )
        
        # Set raw values for all
        model.raw_values = {f"val{i}": float(i) / 20.0 for i in range(20)}
        
        # Get channels
        channels = model.getChannels()
        
        # Should only return 14
        assert len(channels) == 14
        
        # First 14 should have values
        for i in range(14):
            assert channels[i] == float(i) / 20.0

    def test_getchannels_with_missing_value(self):
        """getChannels() should handle missing values gracefully."""
        ctrl1 = VirtualControl(name="ctrl1", control_type=ControlType.BIPOLAR)
        ctrl2 = VirtualControl(name="ctrl2", control_type=ControlType.UNIPOLAR)

        model = Model(
            name="test",
            model_id="test123",
            values=[
                Value(name="val1", control=ctrl1),
                Value(name="val2", control=ctrl2),
            ],
            channels=Channels(
                ch_1="val1",
                ch_2="nonexistent",  # This value doesn't exist
                ch_3="val2",
            ),
        )

        model.raw_values = {"val1": 0.5, "val2": 0.8}

        channels = model.getChannels()

        assert channels[0] == 0.5
        assert channels[1] == 0.0  # Missing value defaults to 0.0
        assert channels[2] == 0.8

    def test_channels_class_all_optional(self):
        """All Channels fields should be optional."""
        # Should be able to create with no arguments
        ch = Channels()

        assert ch.ch_1 is None
        assert ch.ch_2 is None
        assert ch.ch_14 is None

    def test_channels_class_partial_mapping(self):
        """Should be able to set only some channels."""
        ch = Channels(
            ch_1="throttle",
            ch_5="steering",
        )

        assert ch.ch_1 == "throttle"
        assert ch.ch_2 is None
        assert ch.ch_5 == "steering"
        assert ch.ch_14 is None
