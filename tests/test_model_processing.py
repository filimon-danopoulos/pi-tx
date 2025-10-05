"""
Unit tests for the Model processing architecture.

Tests the three-stage processing:
1. Raw value collection (in raw_values)
2. Processing stage (_process): applies mixes -> processed_values
3. Post-processing stage (_postProcess): applies reversing and endpoints
"""

import pytest
from pi_tx.domain import (
    Model,
    Channel,
    Endpoint,
    DifferentialMix,
    AggregateMix,
    AggregateSource,
    VirtualControl,
)
from pi_tx.domain.stick_mapping import ControlType


class TestRawValuesInitialization:
    """Test that raw_values and processed_values are initialized."""

    def test_model_initializes_raw_values(self):
        """raw_values should be initialized as empty dict."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl)],
        )
        assert hasattr(model, "raw_values")
        assert isinstance(model.raw_values, dict)
        assert len(model.raw_values) == 0

    def test_model_initializes_processed_values(self):
        """processed_values should be initialized as empty dict."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl)],
        )
        assert hasattr(model, "processed_values")
        assert isinstance(model.processed_values, dict)
        assert len(model.processed_values) == 0


class TestReadValuesBasic:
    """Test readValues() with basic scenarios."""

    def test_read_values_with_no_raw_values(self):
        """readValues() should return all channels with 0.0 when no raw values."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl)],
        )
        result = model.readValues()
        assert result == {"ch1": 0.0}

    def test_read_values_with_single_channel(self):
        """readValues() should process a single channel."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl)],
        )
        model.raw_values = {"ch1": 0.5}
        result = model.readValues()
        assert result == {"ch1": 0.5}

    def test_read_values_with_multiple_channels(self):
        """readValues() should process multiple channels."""
        virtual_ctrl1 = VirtualControl(name="ctrl1", control_type=ControlType.BIPOLAR)
        virtual_ctrl2 = VirtualControl(name="ctrl2", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=virtual_ctrl1),
                Channel(name="ch2", control=virtual_ctrl2),
            ],
        )
        model.raw_values = {"ch1": 0.5, "ch2": -0.3}
        result = model.readValues()
        assert result == {"ch1": 0.5, "ch2": -0.3}

    def test_read_values_returns_copy_of_processed_values(self):
        """readValues() should return a copy of processed_values dict."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl)],
        )
        model.raw_values = {"ch1": 0.7}
        result = model.readValues()
        # Should be a copy, not the same object
        assert result is not model.processed_values
        # But should have the same content
        assert result == model.processed_values
        assert result == {"ch1": 0.7}


class TestProcessMethod:
    """Test the _process() method for mixing."""

    def test_process_without_mixes(self):
        """_process() should copy raw_values to processed_values when no mixes."""
        virtual_ctrl1 = VirtualControl(name="ctrl1", control_type=ControlType.BIPOLAR)
        virtual_ctrl2 = VirtualControl(name="ctrl2", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=virtual_ctrl1),
                Channel(name="ch2", control=virtual_ctrl2),
            ],
        )
        model.raw_values = {"ch1": 0.5, "ch2": -0.3}
        model._process()
        assert model.processed_values == {"ch1": 0.5, "ch2": -0.3}

    def test_process_with_differential_mix(self):
        """_process() should apply differential mixing."""
        virtual_left = VirtualControl(name="left", control_type=ControlType.BIPOLAR)
        virtual_right = VirtualControl(name="right", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="left_track", control=virtual_left),
                Channel(name="right_track", control=virtual_right),
            ],
            mixes=[
                DifferentialMix(
                    left_channel="left_track",
                    right_channel="right_track",
                    inverse=False,
                )
            ],
        )
        
        # Test forward motion (both same)
        model.raw_values = {"left_track": 0.5, "right_track": 0.5}
        model._process()
        assert abs(model.processed_values["left_track"] - 0.5) < 1e-6
        assert abs(model.processed_values["right_track"] - 0.5) < 1e-6

    def test_process_with_differential_mix_turn(self):
        """_process() should calculate turn correctly in differential mix."""
        virtual_left = VirtualControl(name="left", control_type=ControlType.BIPOLAR)
        virtual_right = VirtualControl(name="right", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="left_track", control=virtual_left),
                Channel(name="right_track", control=virtual_right),
            ],
            mixes=[
                DifferentialMix(
                    left_channel="left_track",
                    right_channel="right_track",
                )
            ],
        )
        
        # Forward + Turn: left=0.2, right=0.8
        # forward = (0.2 + 0.8) / 2 = 0.5
        # turn = (0.8 - 0.2) / 2 = 0.3
        # new_left = 0.5 - 0.3 = 0.2
        # new_right = 0.5 + 0.3 = 0.8
        model.raw_values = {"left_track": 0.2, "right_track": 0.8}
        model._process()
        assert abs(model.processed_values["left_track"] - 0.2) < 1e-6
        assert abs(model.processed_values["right_track"] - 0.8) < 1e-6

    def test_process_with_differential_mix_inverse(self):
        """_process() should swap outputs when inverse=True."""
        virtual_left = VirtualControl(name="left", control_type=ControlType.BIPOLAR)
        virtual_right = VirtualControl(name="right", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="left_track", control=virtual_left),
                Channel(name="right_track", control=virtual_right),
            ],
            mixes=[
                DifferentialMix(
                    left_channel="left_track",
                    right_channel="right_track",
                    inverse=True,
                )
            ],
        )
        
        model.raw_values = {"left_track": 0.2, "right_track": 0.8}
        model._process()
        # With inverse, the values should be swapped
        assert abs(model.processed_values["left_track"] - 0.8) < 1e-6
        assert abs(model.processed_values["right_track"] - 0.2) < 1e-6

    def test_process_with_aggregate_mix(self):
        """_process() should apply aggregate mixing."""
        virtual_ch1 = VirtualControl(name="ch1", control_type=ControlType.BIPOLAR)
        virtual_ch2 = VirtualControl(name="ch2", control_type=ControlType.BIPOLAR)
        virtual_sound = VirtualControl(name="sound", control_type=ControlType.UNIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=virtual_ch1),
                Channel(name="ch2", control=virtual_ch2),
                Channel(name="sound", control=virtual_sound),
            ],
            mixes=[
                AggregateMix(
                    sources=[
                        AggregateSource(channel_name="ch1", weight=0.5),
                        AggregateSource(channel_name="ch2", weight=0.5),
                    ],
                    target_channel="sound",
                )
            ],
        )
        
        # |0.6| * 0.5 + |-0.4| * 0.5 = 0.3 + 0.2 = 0.5
        model.raw_values = {"ch1": 0.6, "ch2": -0.4, "sound": 0.0}
        model._process()
        assert abs(model.processed_values["sound"] - 0.5) < 1e-6

    def test_process_with_aggregate_mix_clamping(self):
        """_process() should clamp aggregate values to [0, 1]."""
        virtual_ch1 = VirtualControl(name="ch1", control_type=ControlType.BIPOLAR)
        virtual_ch2 = VirtualControl(name="ch2", control_type=ControlType.BIPOLAR)
        virtual_sound = VirtualControl(name="sound", control_type=ControlType.UNIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=virtual_ch1),
                Channel(name="ch2", control=virtual_ch2),
                Channel(name="sound", control=virtual_sound),
            ],
            mixes=[
                AggregateMix(
                    sources=[
                        AggregateSource(channel_name="ch1", weight=0.8),
                        AggregateSource(channel_name="ch2", weight=0.8),
                    ],
                    target_channel="sound",
                )
            ],
        )
        
        # 1.0 * 0.8 + 1.0 * 0.8 = 1.6 -> clamped to 1.0
        model.raw_values = {"ch1": 1.0, "ch2": 1.0, "sound": 0.0}
        model._process()
        assert model.processed_values["sound"] == 1.0


class TestPostProcessMethod:
    """Test the _postProcess() method for reversing and endpoints."""

    def test_post_process_without_reversing(self):
        """_postProcess() should not modify values when no reversing."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl, reversed=False)],
        )
        model.processed_values = {"ch1": 0.5}
        model._postProcess()
        assert model.processed_values["ch1"] == 0.5

    def test_post_process_with_bipolar_reversing(self):
        """_postProcess() should negate bipolar values when reversed."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl, reversed=True)],
        )
        model.processed_values = {"ch1": 0.5}
        model._postProcess()
        assert model.processed_values["ch1"] == -0.5

    def test_post_process_with_unipolar_reversing(self):
        """_postProcess() should invert unipolar values when reversed."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.UNIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl, reversed=True)],
        )
        model.processed_values = {"ch1": 0.7}
        model._postProcess()
        assert abs(model.processed_values["ch1"] - 0.3) < 1e-6  # 1.0 - 0.7

    def test_post_process_applies_endpoints(self):
        """_postProcess() should clamp values to endpoint range."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(
                    name="ch1",
                    control=virtual_ctrl,
                    endpoint=Endpoint(min=-0.5, max=0.5),
                )
            ],
        )
        
        # Test clamping to max
        model.processed_values = {"ch1": 0.8}
        model._postProcess()
        assert model.processed_values["ch1"] == 0.5
        
        # Test clamping to min
        model.processed_values = {"ch1": -0.9}
        model._postProcess()
        assert model.processed_values["ch1"] == -0.5
        
        # Test no clamping when in range
        model.processed_values = {"ch1": 0.3}
        model._postProcess()
        assert model.processed_values["ch1"] == 0.3

    def test_post_process_applies_reversing_before_endpoints(self):
        """_postProcess() should reverse first, then clamp."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(
                    name="ch1",
                    control=virtual_ctrl,
                    reversed=True,
                    endpoint=Endpoint(min=-0.5, max=0.5),
                )
            ],
        )
        
        # 0.8 -> reversed to -0.8 -> clamped to -0.5
        model.processed_values = {"ch1": 0.8}
        model._postProcess()
        assert model.processed_values["ch1"] == -0.5


class TestIntegratedProcessing:
    """Test the full processing pipeline through readValues()."""

    def test_read_values_full_pipeline_no_mixes(self):
        """readValues() should process values through all stages."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(
                    name="ch1",
                    control=virtual_ctrl,
                    reversed=True,
                    endpoint=Endpoint(min=-0.6, max=0.6),
                )
            ],
        )
        
        # 0.5 -> reversed to -0.5 -> no clamping needed
        model.raw_values = {"ch1": 0.5}
        result = model.readValues()
        assert result["ch1"] == -0.5

    def test_read_values_with_differential_and_reversing(self):
        """readValues() should apply mixes then reversing."""
        virtual_left = VirtualControl(name="left", control_type=ControlType.BIPOLAR)
        virtual_right = VirtualControl(name="right", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="left_track", control=virtual_left, reversed=True),
                Channel(name="right_track", control=virtual_right, reversed=False),
            ],
            mixes=[
                DifferentialMix(
                    left_channel="left_track",
                    right_channel="right_track",
                )
            ],
        )
        
        # After diff mix: left=0.6, right=0.4
        # After reversing: left=-0.6, right=0.4
        model.raw_values = {"left_track": 0.6, "right_track": 0.4}
        result = model.readValues()
        assert abs(result["left_track"] - (-0.6)) < 1e-6
        assert abs(result["right_track"] - 0.4) < 1e-6

    def test_read_values_complex_model(self):
        """readValues() with differential mix, aggregate mix, reversing, and endpoints."""
        virtual_left = VirtualControl(name="left", control_type=ControlType.BIPOLAR)
        virtual_right = VirtualControl(name="right", control_type=ControlType.BIPOLAR)
        virtual_sound = VirtualControl(name="sound", control_type=ControlType.UNIPOLAR)
        
        model = Model(
            name="complex",
            model_id="complex123",
            channels=[
                Channel(
                    name="left_track",
                    control=virtual_left,
                    reversed=True,
                    endpoint=Endpoint(min=-0.8, max=0.8),
                ),
                Channel(
                    name="right_track",
                    control=virtual_right,
                    reversed=False,
                    endpoint=Endpoint(min=-0.8, max=0.8),
                ),
                Channel(name="sound", control=virtual_sound),
            ],
            mixes=[
                DifferentialMix(
                    left_channel="left_track",
                    right_channel="right_track",
                ),
                AggregateMix(
                    sources=[
                        AggregateSource(channel_name="left_track", weight=0.5),
                        AggregateSource(channel_name="right_track", weight=0.5),
                    ],
                    target_channel="sound",
                ),
            ],
        )
        
        model.raw_values = {"left_track": 0.6, "right_track": 0.4, "sound": 0.0}
        result = model.readValues()
        
        # After differential: left=0.6, right=0.4
        # After aggregate: sound = |0.6|*0.5 + |0.4|*0.5 = 0.5
        # After reversing: left=-0.6, right=0.4, sound=0.5
        # After endpoints: all within range
        assert abs(result["left_track"] - (-0.6)) < 1e-6
        assert abs(result["right_track"] - 0.4) < 1e-6
        assert abs(result["sound"] - 0.5) < 1e-6

    def test_read_values_multiple_calls(self):
        """readValues() should be idempotent with same raw_values."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl, reversed=True)],
        )
        
        model.raw_values = {"ch1": 0.5}
        result1 = model.readValues()
        result2 = model.readValues()
        
        assert result1 == result2
        assert result1["ch1"] == -0.5

    def test_read_values_updates_with_new_raw_values(self):
        """readValues() should reflect changes to raw_values."""
        virtual_ctrl = VirtualControl(name="ctrl", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[Channel(name="ch1", control=virtual_ctrl)],
        )
        
        model.raw_values = {"ch1": 0.5}
        result1 = model.readValues()
        assert result1["ch1"] == 0.5
        
        model.raw_values = {"ch1": 0.8}
        result2 = model.readValues()
        assert result2["ch1"] == 0.8


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_process_handles_missing_channel_in_raw_values(self):
        """_process() should only process channels present in raw_values or mixes."""
        virtual_ctrl1 = VirtualControl(name="ctrl1", control_type=ControlType.BIPOLAR)
        virtual_ctrl2 = VirtualControl(name="ctrl2", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=virtual_ctrl1),
                Channel(name="ch2", control=virtual_ctrl2),
            ],
        )
        
        # Only ch1 in raw_values
        model.raw_values = {"ch1": 0.5}
        model._process()
        # After _process, processed_values only has ch1
        assert model.processed_values["ch1"] == 0.5
        assert "ch2" not in model.processed_values
        
        # But after _postProcess, all channels will be present
        model._postProcess()
        assert model.processed_values["ch1"] == 0.5
        assert model.processed_values["ch2"] == 0.0

    def test_post_process_handles_missing_channel_in_processed_values(self):
        """_postProcess() should use 0.0 for missing channels."""
        virtual_ctrl1 = VirtualControl(name="ctrl1", control_type=ControlType.BIPOLAR)
        virtual_ctrl2 = VirtualControl(name="ctrl2", control_type=ControlType.BIPOLAR)
        model = Model(
            name="test",
            model_id="test123",
            channels=[
                Channel(name="ch1", control=virtual_ctrl1),
                Channel(name="ch2", control=virtual_ctrl2, reversed=True),
            ],
        )
        
        # Only ch1 in processed_values
        model.processed_values = {"ch1": 0.5}
        model._postProcess()
        assert model.processed_values["ch1"] == 0.5
        assert model.processed_values["ch2"] == 0.0  # 0.0 reversed is still 0.0

    def test_read_values_empty_model(self):
        """readValues() should work with model that has no channels."""
        model = Model(
            name="empty",
            model_id="empty123",
            channels=[],
        )
        result = model.readValues()
        assert result == {}
