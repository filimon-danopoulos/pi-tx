"""
Unit tests for Channel latching functionality.

Tests the latching flag on Channel which toggles output state on rising edges.
Latching is applied at the input stage (preProcess), not during channel 
post-processing. This means latching happens on raw normalized values 
before mixing.
"""

import pytest
from pi_tx.domain.models import Channel, Endpoint, VirtualControl
from pi_tx.input.mappings.stick_mapping import ControlType


class TestChannelLatching:
    """Test the latching flag on Channel."""

    def test_latching_disabled_passes_through(self):
        """When latching is False, value should pass through preProcess unchanged."""
        ctrl = VirtualControl(name="test", control_type=ControlType.BUTTON)
        channel = Channel(name="ch1", control=ctrl, latching=False)
        
        # Values should pass through unchanged in preProcess
        assert channel.preProcess(0.0) == 0.0
        assert channel.preProcess(1.0) == 1.0
        assert channel.preProcess(0.5) == 0.5

    def test_latching_enabled_toggles_on_rising_edge(self):
        """When latching is True, output should toggle on 0->non-zero transitions."""
        ctrl = VirtualControl(name="test", control_type=ControlType.BUTTON)
        channel = Channel(name="ch1", control=ctrl, latching=True)
        
        # Initial state should be 0.0
        assert channel.preProcess(0.0) == 0.0
        
        # First rising edge: 0 -> 1, should toggle to 1.0
        assert channel.preProcess(1.0) == 1.0
        
        # Staying at 1.0 should keep state at 1.0
        assert channel.preProcess(1.0) == 1.0
        
        # Going back to 0 should keep state at 1.0
        assert channel.preProcess(0.0) == 1.0
        
        # Second rising edge: 0 -> 1, should toggle back to 0.0
        assert channel.preProcess(1.0) == 0.0
        
        # Staying at 1.0 should keep state at 0.0
        assert channel.preProcess(1.0) == 0.0
        
        # Going back to 0 should keep state at 0.0
        assert channel.preProcess(0.0) == 0.0
        
        # Third rising edge: 0 -> 1, should toggle to 1.0 again
        assert channel.preProcess(1.0) == 1.0

    def test_latching_with_non_zero_values(self):
        """Latching should work with any non-zero value."""
        ctrl = VirtualControl(name="test", control_type=ControlType.UNIPOLAR)
        channel = Channel(name="ch1", control=ctrl, latching=True)
        
        # Initial state
        assert channel.preProcess(0.0) == 0.0
        
        # Rising edge with 0.7
        assert channel.preProcess(0.7) == 1.0
        
        # Different non-zero value should not toggle
        assert channel.preProcess(0.5) == 1.0
        
        # Back to zero
        assert channel.preProcess(0.0) == 1.0
        
        # Rising edge with 0.3
        assert channel.preProcess(0.3) == 0.0
        
        # Back to zero
        assert channel.preProcess(0.0) == 0.0
        
        # Rising edge with 1.0
        assert channel.preProcess(1.0) == 1.0

    def test_latching_with_reversing(self):
        """Latching is applied in preProcess, reversing in postProcess."""
        ctrl = VirtualControl(name="test", control_type=ControlType.UNIPOLAR)
        channel = Channel(name="ch1", control=ctrl, latching=True, reversed=True)
        
        # Initial state in preProcess
        preprocessed = channel.preProcess(0.0)
        assert preprocessed == 0.0
        # After postProcess reversing: 1.0 - 0.0 = 1.0
        assert channel.postProcess(preprocessed) == 1.0
        
        # First toggle to 1.0 in preProcess
        preprocessed = channel.preProcess(1.0)
        assert preprocessed == 1.0
        # After postProcess reversing: 1.0 - 1.0 = 0.0
        assert channel.postProcess(preprocessed) == 0.0
        
        # Release (back to 0), latch state stays at 1.0
        preprocessed = channel.preProcess(0.0)
        assert preprocessed == 1.0
        # After postProcess reversing: 1.0 - 1.0 = 0.0
        assert channel.postProcess(preprocessed) == 0.0
        
        # Second toggle back to 0.0 in preProcess
        preprocessed = channel.preProcess(1.0)
        assert preprocessed == 0.0
        # After postProcess reversing: 1.0 - 0.0 = 1.0
        assert channel.postProcess(preprocessed) == 1.0

    def test_latching_with_bipolar_reversing(self):
        """Latching with bipolar control type reverses with negation."""
        ctrl = VirtualControl(name="test", control_type=ControlType.BIPOLAR)
        channel = Channel(name="ch1", control=ctrl, latching=True, reversed=True)
        
        # Initial state: 0.0 in preProcess
        preprocessed = channel.preProcess(0.0)
        assert preprocessed == 0.0
        # reversed (bipolar): -0.0 = 0.0
        assert channel.postProcess(preprocessed) == 0.0
        
        # First toggle to 1.0 in preProcess
        preprocessed = channel.preProcess(1.0)
        assert preprocessed == 1.0
        # reversed (bipolar): -1.0
        assert channel.postProcess(preprocessed) == -1.0
        
        # Release, latch state stays at 1.0
        preprocessed = channel.preProcess(0.0)
        assert preprocessed == 1.0
        # reversed (bipolar): -1.0
        assert channel.postProcess(preprocessed) == -1.0
        
        # Second toggle to 0.0 in preProcess
        preprocessed = channel.preProcess(1.0)
        assert preprocessed == 0.0
        # reversed (bipolar): -0.0 = 0.0
        assert channel.postProcess(preprocessed) == 0.0

    def test_latching_with_endpoints(self):
        """Latching is applied in preProcess, endpoints in postProcess."""
        ctrl = VirtualControl(name="test", control_type=ControlType.UNIPOLAR)
        channel = Channel(
            name="ch1",
            control=ctrl,
            latching=True,
            endpoint=Endpoint(min=0.2, max=0.8)
        )
        
        # Initial state: 0.0 in preProcess
        preprocessed = channel.preProcess(0.0)
        assert preprocessed == 0.0
        # clamped to min 0.2
        assert channel.postProcess(preprocessed) == 0.2
        
        # First toggle to 1.0 in preProcess
        preprocessed = channel.preProcess(1.0)
        assert preprocessed == 1.0
        # clamped to max 0.8
        assert channel.postProcess(preprocessed) == 0.8
        
        # Release, latch state stays at 1.0
        preprocessed = channel.preProcess(0.0)
        assert preprocessed == 1.0
        # still 1.0, clamped to max 0.8
        assert channel.postProcess(preprocessed) == 0.8
        
        # Second toggle to 0.0 in preProcess
        preprocessed = channel.preProcess(1.0)
        assert preprocessed == 0.0
        # clamped to min 0.2
        assert channel.postProcess(preprocessed) == 0.2

    def test_latching_multiple_rapid_transitions(self):
        """Latching should handle rapid on/off/on transitions correctly."""
        ctrl = VirtualControl(name="test", control_type=ControlType.BUTTON)
        channel = Channel(name="ch1", control=ctrl, latching=True)
        
        # Sequence: 0, 1 (toggle), 0, 1 (toggle), 0, 1 (toggle), 0
        assert channel.preProcess(0.0) == 0.0  # Initial
        assert channel.preProcess(1.0) == 1.0  # First press
        assert channel.preProcess(0.0) == 1.0  # Release
        assert channel.preProcess(1.0) == 0.0  # Second press
        assert channel.preProcess(0.0) == 0.0  # Release
        assert channel.preProcess(1.0) == 1.0  # Third press
        assert channel.preProcess(0.0) == 1.0  # Release

    def test_latching_state_persistence(self):
        """Latching state should persist across many zero inputs."""
        ctrl = VirtualControl(name="test", control_type=ControlType.BUTTON)
        channel = Channel(name="ch1", control=ctrl, latching=True)
        
        # Toggle on
        channel.preProcess(0.0)
        channel.preProcess(1.0)
        assert channel.preProcess(0.0) == 1.0
        
        # Many zeros should not change state
        for _ in range(100):
            assert channel.preProcess(0.0) == 1.0
        
        # Toggle off
        assert channel.preProcess(1.0) == 0.0
        
        # Many zeros should keep it off
        for _ in range(100):
            assert channel.preProcess(0.0) == 0.0

    def test_latching_combined_with_all_features(self):
        """Test latching combined with reversing and endpoints."""
        ctrl = VirtualControl(name="test", control_type=ControlType.UNIPOLAR)
        channel = Channel(
            name="ch1",
            control=ctrl,
            latching=True,
            reversed=True,
            endpoint=Endpoint(min=0.1, max=0.9)
        )
        
        # Initial: preProcess 0.0 -> 0.0, postProcess reversed to 1.0 -> clamped to 0.9
        preprocessed = channel.preProcess(0.0)
        assert preprocessed == 0.0
        assert channel.postProcess(preprocessed) == 0.9
        
        # Toggle: preProcess 1.0 -> 1.0, postProcess reversed to 0.0 -> clamped to 0.1
        preprocessed = channel.preProcess(1.0)
        assert preprocessed == 1.0
        assert channel.postProcess(preprocessed) == 0.1
        
        # Release: preProcess 0.0 -> stays 1.0, postProcess reversed to 0.0 -> clamped to 0.1
        preprocessed = channel.preProcess(0.0)
        assert preprocessed == 1.0
        assert channel.postProcess(preprocessed) == 0.1
        
        # Toggle: preProcess 1.0 -> 0.0, postProcess reversed to 1.0 -> clamped to 0.9
        preprocessed = channel.preProcess(1.0)
        assert preprocessed == 0.0
        assert channel.postProcess(preprocessed) == 0.9

    def test_latching_initialization(self):
        """Channel should initialize with latching state at 0.0."""
        ctrl = VirtualControl(name="test", control_type=ControlType.BUTTON)
        channel = Channel(name="ch1", control=ctrl, latching=True)
        
        # Before any input, state should be 0.0
        assert hasattr(channel, '_latch_state')
        assert channel._latch_state == 0.0
        assert hasattr(channel, '_last_input')
        assert channel._last_input == 0.0
