"""Tests for example model definitions."""
import pytest
from examples.model_definitions import D6TModel, SimpleModel, CustomD6TModel


def test_d6t_model_build():
    """Test that D6TModel builds successfully."""
    model = D6TModel().build()
    
    assert model.name == "cat_d6t"
    assert model.model_id == "f2f9b6c8c2e44d3d8947e7d6b8c6e5ab"
    assert model.rx_num == 1
    
    # Check channels
    assert len(model.channels) == 7
    assert 1 in model.channels
    assert 7 in model.channels
    
    # Check channel types
    assert model.channels[1].control_type == "bipolar"
    assert model.channels[6].control_type == "latching-button"
    assert model.channels[7].control_type == "unipolar"
    assert model.channels[7].control_code == "virtual"
    
    # Check processors exist
    assert "reverse" in model.processors
    assert "endpoints" in model.processors
    assert "differential" in model.processors
    assert "aggregate" in model.processors


def test_d6t_model_reverse_processor():
    """Test D6TModel reverse processor configuration."""
    model = D6TModel().build()
    
    reverse = model.processors["reverse"]
    assert reverse["ch1"] is True
    assert reverse["ch2"] is False
    assert reverse["ch3"] is True
    assert reverse["ch5"] is True
    assert reverse["ch7"] is True


def test_d6t_model_endpoints():
    """Test D6TModel endpoint processor configuration."""
    model = D6TModel().build()
    
    endpoints = model.processors["endpoints"]
    assert endpoints["ch1"]["min"] == -0.80
    assert endpoints["ch1"]["max"] == 0.90
    assert endpoints["ch3"]["min"] == -0.50
    assert endpoints["ch3"]["max"] == 0.70
    assert endpoints["ch7"]["min"] == 0.00
    assert endpoints["ch7"]["max"] == 1.00


def test_d6t_model_differential():
    """Test D6TModel differential processor configuration."""
    model = D6TModel().build()
    
    differential = model.processors["differential"]
    assert len(differential) == 2
    assert differential[0]["left"] == "ch2"
    assert differential[0]["right"] == "ch1"
    assert differential[0]["inverse"] is True
    assert differential[1]["left"] == "ch4"
    assert differential[1]["right"] == "ch3"
    assert differential[1]["inverse"] is False


def test_d6t_model_aggregate():
    """Test D6TModel aggregate processor configuration."""
    model = D6TModel().build()
    
    aggregate = model.processors["aggregate"]
    assert len(aggregate) == 1
    
    mix = aggregate[0]
    assert mix["target"] == "ch7"
    assert len(mix["channels"]) == 4
    
    # Check channel weights
    assert mix["channels"][0]["id"] == "ch1"
    assert mix["channels"][0]["value"] == 0.2
    assert mix["channels"][2]["id"] == "ch3"
    assert mix["channels"][2]["value"] == 0.4


def test_simple_model():
    """Test SimpleModel builds successfully."""
    model = SimpleModel("simple_test").build()
    
    assert model.name == "simple_test"
    assert model.rx_num == 0
    assert len(model.channels) == 2
    assert model.channels[1].control_type == "bipolar"
    assert model.channels[1].control_name == "X-axis"
    assert model.channels[2].control_name == "Y-axis"


def test_custom_d6t_model():
    """Test CustomD6TModel with customization."""
    model = CustomD6TModel().build()
    
    # Check customized properties
    assert model.name == "custom_d6t"
    assert model.rx_num == 2
    
    # Should have the extra virtual channel
    assert len(model.channels) == 8
    assert 8 in model.channels
    assert model.channels[8].control_code == "virtual"
    assert model.channels[8].control_name == "extra-virtual"
    
    # Should still have all the base channels and processors
    assert "reverse" in model.processors
    assert "differential" in model.processors


def test_d6t_model_channel_device_paths():
    """Test that D6TModel has correct device paths."""
    model = D6TModel().build()
    
    # Channels 1, 2, 5, 6 should use STICK_1_PATH
    stick1_path = "/dev/input/by-path/pci-0000:00:14.0-usb-0:3:1.0-event-joystick"
    assert model.channels[1].device_path == stick1_path
    assert model.channels[2].device_path == stick1_path
    assert model.channels[5].device_path == stick1_path
    assert model.channels[6].device_path == stick1_path
    
    # Channels 3, 4 should use STICK_2_PATH
    stick2_path = "/dev/input/by-path/pci-0000:00:14.0-usb-0:2:1.0-event-joystick"
    assert model.channels[3].device_path == stick2_path
    assert model.channels[4].device_path == stick2_path
    
    # Channel 7 is virtual
    assert model.channels[7].device_path == ""


def test_d6t_model_subclass_override():
    """Test that D6TModel can be subclassed and device paths overridden."""
    
    class TestD6T(D6TModel):
        STICK_1_PATH = "/dev/test/stick1"
        STICK_2_PATH = "/dev/test/stick2"
    
    model = TestD6T().build()
    
    assert model.channels[1].device_path == "/dev/test/stick1"
    assert model.channels[3].device_path == "/dev/test/stick2"
