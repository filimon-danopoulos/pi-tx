"""
Integration tests for Channel latching within Model processing.

Tests latching behavior through the full Model processing pipeline.
Since latching happens in preProcess (at the input stage), these tests
simulate the flow by calling preProcess on channels before readValues.
"""

import pytest
from pi_tx.domain.models import (
    Model,
    Channel,
    Endpoint,
    VirtualControl,
)
from pi_tx.input.mappings.stick_mapping import ControlType


class TestLatchingInModelProcessing:
    """Test latching channels within full model processing."""

    def test_latching_channel_in_model(self):
        """Latching should work through full Model.readValues() pipeline."""
        button_ctrl = VirtualControl(name="btn", control_type=ControlType.BUTTON)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="gear", control=button_ctrl, latching=True),
            ],
        )

        # Simulate input flow: preProcess happens during listen(), then readValues()
        gear_channel = model.get_channel_by_name("gear")

        # Initial state
        model.raw_values = {"gear": gear_channel.preProcess(0.0)}
        assert model.readValues()["gear"] == 0.0

        # First press
        model.raw_values = {"gear": gear_channel.preProcess(1.0)}
        assert model.readValues()["gear"] == 1.0

        # Release
        model.raw_values = {"gear": gear_channel.preProcess(0.0)}
        assert model.readValues()["gear"] == 1.0

        # Second press
        model.raw_values = {"gear": gear_channel.preProcess(1.0)}
        assert model.readValues()["gear"] == 0.0

    def test_multiple_latching_channels_independent(self):
        """Multiple latching channels should maintain independent state."""
        btn1 = VirtualControl(name="btn1", control_type=ControlType.BUTTON)
        btn2 = VirtualControl(name="btn2", control_type=ControlType.BUTTON)

        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=btn1, latching=True),
                Channel(name="ch2", control=btn2, latching=True),
            ],
        )

        ch1 = model.get_channel_by_name("ch1")
        ch2 = model.get_channel_by_name("ch2")

        # Toggle ch1 on
        model.raw_values = {"ch1": ch1.preProcess(0.0), "ch2": ch2.preProcess(0.0)}
        model.readValues()
        model.raw_values = {"ch1": ch1.preProcess(1.0), "ch2": ch2.preProcess(0.0)}
        result = model.readValues()
        assert result["ch1"] == 1.0
        assert result["ch2"] == 0.0

        # Toggle ch2 on (ch1 stays on)
        model.raw_values = {"ch1": ch1.preProcess(1.0), "ch2": ch2.preProcess(0.0)}
        model.readValues()
        model.raw_values = {"ch1": ch1.preProcess(1.0), "ch2": ch2.preProcess(1.0)}
        result = model.readValues()
        assert result["ch1"] == 1.0
        assert result["ch2"] == 1.0

        # Toggle ch1 off (ch2 stays on)
        model.raw_values = {"ch1": ch1.preProcess(1.0), "ch2": ch2.preProcess(1.0)}
        model.readValues()
        model.raw_values = {"ch1": ch1.preProcess(0.0), "ch2": ch2.preProcess(1.0)}
        model.readValues()
        model.raw_values = {"ch1": ch1.preProcess(1.0), "ch2": ch2.preProcess(1.0)}
        result = model.readValues()
        assert result["ch1"] == 0.0
        assert result["ch2"] == 1.0

    def test_latching_with_reversing_in_model(self):
        """Latching combined with reversing in model context."""
        btn = VirtualControl(name="btn", control_type=ControlType.UNIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=btn, latching=True, reversed=True),
            ],
        )

        ch1 = model.get_channel_by_name("ch1")

        # Initial: preProcess 0.0 -> 0.0, postProcess reversed -> 1.0
        model.raw_values = {"ch1": ch1.preProcess(0.0)}
        assert model.readValues()["ch1"] == 1.0

        # Toggle: preProcess 1.0 -> 1.0, postProcess reversed -> 0.0
        model.raw_values = {"ch1": ch1.preProcess(1.0)}
        assert model.readValues()["ch1"] == 0.0

        # Release: preProcess 0.0 -> stays 1.0, postProcess reversed -> 0.0
        model.raw_values = {"ch1": ch1.preProcess(0.0)}
        assert model.readValues()["ch1"] == 0.0

        # Toggle again: preProcess 1.0 -> 0.0, postProcess reversed -> 1.0
        model.raw_values = {"ch1": ch1.preProcess(1.0)}
        assert model.readValues()["ch1"] == 1.0

    def test_latching_with_endpoints_in_model(self):
        """Latching combined with endpoints in model context."""
        btn = VirtualControl(name="btn", control_type=ControlType.BUTTON)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(
                    name="ch1",
                    control=btn,
                    latching=True,
                    endpoint=Endpoint(min=0.3, max=0.7),
                ),
            ],
        )

        ch1 = model.get_channel_by_name("ch1")

        # preProcess 0.0 -> 0.0, postProcess clamped to 0.3
        model.raw_values = {"ch1": ch1.preProcess(0.0)}
        assert model.readValues()["ch1"] == 0.3

        # preProcess 1.0 -> 1.0, postProcess clamped to 0.7
        model.raw_values = {"ch1": ch1.preProcess(1.0)}
        assert model.readValues()["ch1"] == 0.7

    def test_mixed_latching_and_nonlatching_channels(self):
        """Model with both latching and non-latching channels."""
        btn = VirtualControl(name="btn", control_type=ControlType.BUTTON)
        axis = VirtualControl(name="axis", control_type=ControlType.UNIPOLAR)

        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="switch", control=btn, latching=True),
                Channel(name="throttle", control=axis, latching=False),
            ],
        )

        switch_ch = model.get_channel_by_name("switch")
        throttle_ch = model.get_channel_by_name("throttle")

        # Switch toggles, throttle passes through
        model.raw_values = {"switch": switch_ch.preProcess(0.0), "throttle": throttle_ch.preProcess(0.5)}
        result = model.readValues()
        assert result["switch"] == 0.0
        assert result["throttle"] == 0.5

        model.raw_values = {"switch": switch_ch.preProcess(1.0), "throttle": throttle_ch.preProcess(0.7)}
        result = model.readValues()
        assert result["switch"] == 1.0
        assert result["throttle"] == 0.7

        model.raw_values = {"switch": switch_ch.preProcess(0.0), "throttle": throttle_ch.preProcess(0.3)}
        result = model.readValues()
        assert result["switch"] == 1.0  # Stays latched
        assert result["throttle"] == 0.3  # Follows input

    def test_latching_state_persists_across_readvalues_calls(self):
        """Latching state should persist across multiple readValues() calls."""
        btn = VirtualControl(name="btn", control_type=ControlType.BUTTON)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=btn, latching=True),
            ],
        )

        ch1 = model.get_channel_by_name("ch1")

        # Toggle on
        model.raw_values = {"ch1": ch1.preProcess(0.0)}
        model.readValues()
        model.raw_values = {"ch1": ch1.preProcess(1.0)}
        model.readValues()

        # Release and call readValues multiple times
        model.raw_values = {"ch1": ch1.preProcess(0.0)}
        for _ in range(10):
            result = model.readValues()
            assert result["ch1"] == 1.0  # Should stay on

        # Toggle off
        model.raw_values = {"ch1": ch1.preProcess(1.0)}
        model.readValues()

        # Release and call readValues multiple times
        model.raw_values = {"ch1": ch1.preProcess(0.0)}
        for _ in range(10):
            result = model.readValues()
            assert result["ch1"] == 0.0  # Should stay off

    def test_latching_with_all_features(self):
        """Test latching combined with reversing, endpoints, and mixes."""
        from pi_tx.domain.models import AggregateMix, AggregateSource

        btn = VirtualControl(name="btn", control_type=ControlType.BUTTON)
        axis = VirtualControl(name="axis", control_type=ControlType.UNIPOLAR)
        output = VirtualControl(name="output", control_type=ControlType.UNIPOLAR)

        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(
                    name="switch",
                    control=btn,
                    latching=True,
                    reversed=True,
                    endpoint=Endpoint(min=0.2, max=0.8),
                ),
                Channel(name="throttle", control=axis),
                Channel(name="combined", control=output),
            ],
            mixes=[
                AggregateMix(
                    sources=[
                        AggregateSource(channel_name="switch", weight=0.5),
                        AggregateSource(channel_name="throttle", weight=0.5),
                    ],
                    target_channel="combined",
                ),
            ],
        )

        switch_ch = model.get_channel_by_name("switch")
        throttle_ch = model.get_channel_by_name("throttle")

        # Important: AggregateMix uses raw_values (before postProcess)
        # So mixing happens before reversing/endpoints are applied
        
        # Initial state: 
        # - preProcess: switch=0.0 (latched), throttle=0.5
        # - raw_values used for mixing: switch=0.0, throttle=0.5
        # - AggregateMix: |0.0|*0.5 + |0.5|*0.5 = 0.25
        # - postProcess on switch: 0.0 -> reversed 1.0 -> clamped 0.8
        model.raw_values = {
            "switch": switch_ch.preProcess(0.0),
            "throttle": throttle_ch.preProcess(0.5),
            "combined": 0.0
        }
        result = model.readValues()
        assert result["switch"] == 0.8  # 0.0 -> reversed 1.0 -> clamped 0.8
        assert result["throttle"] == 0.5
        assert abs(result["combined"] - 0.25) < 0.01  # Mix uses raw values

        # Toggle switch: preProcess 1.0 -> 1.0
        # - raw_values used for mixing: switch=1.0, throttle=0.5
        # - AggregateMix: |1.0|*0.5 + |0.5|*0.5 = 0.75
        # - postProcess on switch: 1.0 -> reversed 0.0 -> clamped 0.2
        model.raw_values = {
            "switch": switch_ch.preProcess(1.0),
            "throttle": throttle_ch.preProcess(0.5),
            "combined": 0.0
        }
        result = model.readValues()
        assert result["switch"] == 0.2  # 1.0 -> reversed 0.0 -> clamped 0.2
        assert result["throttle"] == 0.5
        assert abs(result["combined"] - 0.75) < 0.01  # Mix uses raw values
