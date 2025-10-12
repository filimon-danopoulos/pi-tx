"""
Unit tests for Value latching functionality.

Tests the latching flag on Value which toggles output state on rising edges.
Latching is applied at the input stage (preProcess), not during channel
post-processing. This means latching happens on raw normalized values
before mixing.
"""

import pytest
from pi_tx.domain import Value, Endpoint
from pi_tx.domain.stick_mapping import ControlType
from test_control import TestControl


class TestValueLatching:
    """Test the latching flag on Value."""

    def test_latching_disabled_passes_through(self):
        """When latching is False, value should pass through preProcess unchanged."""
        ctrl = TestControl(name="test", control_type=ControlType.BUTTON)
        value = Value(name="ch1", control=ctrl, latching=False)

        # Values should pass through unchanged in preProcess
        assert value.preProcess(0.0) == 0.0
        assert value.preProcess(1.0) == 1.0
        assert value.preProcess(0.5) == 0.5

    def test_latching_enabled_toggles_on_rising_edge(self):
        """When latching is True, output should toggle on 0->non-zero transitions."""
        ctrl = TestControl(name="test", control_type=ControlType.BUTTON)
        value = Value(name="ch1", control=ctrl, latching=True)

        # Initial state should be 0.0
        assert value.preProcess(0.0) == 0.0

        # First rising edge: 0 -> 1, should toggle to 1.0
        assert value.preProcess(1.0) == 1.0

        # Staying at 1.0 should keep state at 1.0
        assert value.preProcess(1.0) == 1.0

        # Going back to 0 should keep state at 1.0
        assert value.preProcess(0.0) == 1.0

        # Second rising edge: 0 -> 1, should toggle back to 0.0
        assert value.preProcess(1.0) == 0.0

        # Staying at 1.0 should keep state at 0.0
        assert value.preProcess(1.0) == 0.0

        # Going back to 0 should keep state at 0.0
        assert value.preProcess(0.0) == 0.0

        # Third rising edge: 0 -> 1, should toggle to 1.0 again
        assert value.preProcess(1.0) == 1.0

    def test_latching_with_non_zero_values(self):
        """Latching should work with any non-zero value."""
        ctrl = TestControl(name="test", control_type=ControlType.UNIPOLAR)
        value = Value(name="ch1", control=ctrl, latching=True)

        # Initial state
        assert value.preProcess(0.0) == 0.0

        # Rising edge with 0.7
        assert value.preProcess(0.7) == 1.0

        # Different non-zero value should not toggle
        assert value.preProcess(0.5) == 1.0

        # Back to zero
        assert value.preProcess(0.0) == 1.0

        # Rising edge with 0.3
        assert value.preProcess(0.3) == 0.0

        # Back to zero
        assert value.preProcess(0.0) == 0.0

        # Rising edge with 1.0
        assert value.preProcess(1.0) == 1.0

    def test_latching_with_reversing(self):
        """Latching is applied in preProcess, reversing in postProcess."""
        ctrl = TestControl(name="test", control_type=ControlType.UNIPOLAR)
        value = Value(name="ch1", control=ctrl, latching=True, reversed=True)

        # Initial state in preProcess
        preprocessed = value.preProcess(0.0)
        assert preprocessed == 0.0
        # After postProcess reversing: 1.0 - 0.0 = 1.0
        assert value.postProcess(preprocessed) == 1.0

        # First toggle to 1.0 in preProcess
        preprocessed = value.preProcess(1.0)
        assert preprocessed == 1.0
        # After postProcess reversing: 1.0 - 1.0 = 0.0
        assert value.postProcess(preprocessed) == 0.0

        # Release (back to 0), latch state stays at 1.0
        preprocessed = value.preProcess(0.0)
        assert preprocessed == 1.0
        # After postProcess reversing: 1.0 - 1.0 = 0.0
        assert value.postProcess(preprocessed) == 0.0

        # Second toggle back to 0.0 in preProcess
        preprocessed = value.preProcess(1.0)
        assert preprocessed == 0.0
        # After postProcess reversing: 1.0 - 0.0 = 1.0
        assert value.postProcess(preprocessed) == 1.0

    def test_latching_with_bipolar_reversing(self):
        """Latching with bipolar control type reverses with negation."""
        ctrl = TestControl(name="test", control_type=ControlType.BIPOLAR)
        value = Value(name="ch1", control=ctrl, latching=True, reversed=True)

        # Initial state: 0.0 in preProcess
        preprocessed = value.preProcess(0.0)
        assert preprocessed == 0.0
        # reversed (bipolar): -0.0 = 0.0
        assert value.postProcess(preprocessed) == 0.0

        # First toggle to 1.0 in preProcess
        preprocessed = value.preProcess(1.0)
        assert preprocessed == 1.0
        # reversed (bipolar): -1.0
        assert value.postProcess(preprocessed) == -1.0

        # Release, latch state stays at 1.0
        preprocessed = value.preProcess(0.0)
        assert preprocessed == 1.0
        # reversed (bipolar): -1.0
        assert value.postProcess(preprocessed) == -1.0

        # Second toggle to 0.0 in preProcess
        preprocessed = value.preProcess(1.0)
        assert preprocessed == 0.0
        # reversed (bipolar): -0.0 = 0.0
        assert value.postProcess(preprocessed) == 0.0

    def test_latching_with_endpoints(self):
        """Latching is applied in preProcess, endpoints in postProcess."""
        ctrl = TestControl(name="test", control_type=ControlType.UNIPOLAR)
        value = Value(
            name="ch1", control=ctrl, latching=True, endpoint=Endpoint(min=0.2, max=0.8)
        )

        # Initial state: 0.0 in preProcess
        preprocessed = value.preProcess(0.0)
        assert preprocessed == 0.0
        # clamped to min 0.2
        assert value.postProcess(preprocessed) == 0.2

        # First toggle to 1.0 in preProcess
        preprocessed = value.preProcess(1.0)
        assert preprocessed == 1.0
        # clamped to max 0.8
        assert value.postProcess(preprocessed) == 0.8

        # Release, latch state stays at 1.0
        preprocessed = value.preProcess(0.0)
        assert preprocessed == 1.0
        # still 1.0, clamped to max 0.8
        assert value.postProcess(preprocessed) == 0.8

        # Second toggle to 0.0 in preProcess
        preprocessed = value.preProcess(1.0)
        assert preprocessed == 0.0
        # clamped to min 0.2
        assert value.postProcess(preprocessed) == 0.2

    def test_latching_multiple_rapid_transitions(self):
        """Latching should handle rapid on/off/on transitions correctly."""
        ctrl = TestControl(name="test", control_type=ControlType.BUTTON)
        value = Value(name="ch1", control=ctrl, latching=True)

        # Sequence: 0, 1 (toggle), 0, 1 (toggle), 0, 1 (toggle), 0
        assert value.preProcess(0.0) == 0.0  # Initial
        assert value.preProcess(1.0) == 1.0  # First press
        assert value.preProcess(0.0) == 1.0  # Release
        assert value.preProcess(1.0) == 0.0  # Second press
        assert value.preProcess(0.0) == 0.0  # Release
        assert value.preProcess(1.0) == 1.0  # Third press
        assert value.preProcess(0.0) == 1.0  # Release

    def test_latching_state_persistence(self):
        """Latching state should persist across many zero inputs."""
        ctrl = TestControl(name="test", control_type=ControlType.BUTTON)
        value = Value(name="ch1", control=ctrl, latching=True)

        # Toggle on
        value.preProcess(0.0)
        value.preProcess(1.0)
        assert value.preProcess(0.0) == 1.0

        # Many zeros should not change state
        for _ in range(100):
            assert value.preProcess(0.0) == 1.0

        # Toggle off
        assert value.preProcess(1.0) == 0.0

        # Many zeros should keep it off
        for _ in range(100):
            assert value.preProcess(0.0) == 0.0

    def test_latching_combined_with_all_features(self):
        """Test latching combined with reversing and endpoints."""
        ctrl = TestControl(name="test", control_type=ControlType.UNIPOLAR)
        value = Value(
            name="ch1",
            control=ctrl,
            latching=True,
            reversed=True,
            endpoint=Endpoint(min=0.1, max=0.9),
        )

        # Initial: preProcess 0.0 -> 0.0, postProcess reversed to 1.0 -> clamped to 0.9
        preprocessed = value.preProcess(0.0)
        assert preprocessed == 0.0
        assert value.postProcess(preprocessed) == 0.9

        # Toggle: preProcess 1.0 -> 1.0, postProcess reversed to 0.0 -> clamped to 0.1
        preprocessed = value.preProcess(1.0)
        assert preprocessed == 1.0
        assert value.postProcess(preprocessed) == 0.1

        # Release: preProcess 0.0 -> stays 1.0, postProcess reversed to 0.0 -> clamped to 0.1
        preprocessed = value.preProcess(0.0)
        assert preprocessed == 1.0
        assert value.postProcess(preprocessed) == 0.1

        # Toggle: preProcess 1.0 -> 0.0, postProcess reversed to 1.0 -> clamped to 0.9
        preprocessed = value.preProcess(1.0)
        assert preprocessed == 0.0
        assert value.postProcess(preprocessed) == 0.9

    def test_latching_initialization(self):
        """Channel should initialize with latching state at 0.0."""
        ctrl = TestControl(name="test", control_type=ControlType.BUTTON)
        value = Value(name="ch1", control=ctrl, latching=True)

        # Before any input, state should be 0.0
        assert hasattr(value, "_latch_state")
        assert value._latch_state == 0.0
        assert hasattr(value, "_last_input")
        assert value._last_input == 0.0
