"""Tests for channel classes."""
import pytest
from pi_tx.domain.channel import (
    Channel,
    BipolarChannel,
    UnipolarChannel,
    ButtonChannel,
    LatchingButtonChannel,
    VirtualChannel,
)


def test_bipolar_channel():
    """Test BipolarChannel configuration."""
    ch = BipolarChannel(
        channel_id=1,
        device_path="/dev/input/js0",
        control_code="0",
        device_name="Joystick",
        control_name="X-axis"
    )
    
    assert ch.channel_id == 1
    assert ch.get_control_type() == "bipolar"
    assert ch.device_path == "/dev/input/js0"
    assert ch.control_code == "0"
    
    result = ch.to_dict()
    assert result["control_type"] == "bipolar"
    assert result["device_path"] == "/dev/input/js0"
    assert result["control_code"] == "0"
    assert result["device_name"] == "Joystick"
    assert result["control_name"] == "X-axis"


def test_unipolar_channel():
    """Test UnipolarChannel configuration."""
    ch = UnipolarChannel(
        channel_id=2,
        device_path="/dev/input/js0",
        control_code="2",
        device_name="Joystick",
        control_name="Throttle"
    )
    
    assert ch.get_control_type() == "unipolar"
    assert ch.to_dict()["control_type"] == "unipolar"


def test_button_channel():
    """Test ButtonChannel configuration."""
    ch = ButtonChannel(
        channel_id=3,
        device_path="/dev/input/js0",
        control_code="288",
        device_name="Joystick",
        control_name="Trigger"
    )
    
    assert ch.get_control_type() == "button"
    assert ch.to_dict()["control_type"] == "button"


def test_latching_button_channel():
    """Test LatchingButtonChannel configuration."""
    ch = LatchingButtonChannel(
        channel_id=4,
        device_path="/dev/input/js0",
        control_code="289",
        device_name="Joystick",
        control_name="Button-2"
    )
    
    assert ch.get_control_type() == "latching-button"
    assert ch.to_dict()["control_type"] == "latching-button"


def test_virtual_channel():
    """Test VirtualChannel configuration."""
    ch = VirtualChannel(
        channel_id=5,
        control_name="sound-mix",
        control_type="unipolar"
    )
    
    assert ch.channel_id == 5
    assert ch.get_control_type() == "unipolar"
    assert ch.device_path == ""
    assert ch.control_code == "virtual"
    assert ch.device_name == "virtual"
    assert ch.control_name == "sound-mix"
    
    result = ch.to_dict()
    assert result["control_type"] == "unipolar"
    assert result["device_path"] == ""
    assert result["control_code"] == "virtual"


def test_virtual_channel_bipolar():
    """Test VirtualChannel with bipolar type."""
    ch = VirtualChannel(
        channel_id=6,
        control_name="virtual-bipolar",
        control_type="bipolar"
    )
    
    assert ch.get_control_type() == "bipolar"


def test_channel_optional_fields():
    """Test that optional fields can be omitted."""
    ch = BipolarChannel(
        channel_id=1,
        device_path="/dev/input/js0",
        control_code="0"
    )
    
    # Should still work with empty device_name and control_name
    assert ch.device_name == ""
    assert ch.control_name == ""
    
    result = ch.to_dict()
    # Optional fields should not be in dict if empty
    assert "device_name" not in result
    assert "control_name" not in result
