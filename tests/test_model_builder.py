"""Tests for ModelBuilder class."""
import pytest
from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.model_json import Model
from pi_tx.domain.channel import (
    BipolarChannel,
    UnipolarChannel,
    VirtualChannel,
)
from pi_tx.domain.processors import (
    ReverseProcessor,
    EndpointProcessor,
    DifferentialProcessor,
    DifferentialMix,
)


def test_model_builder_basic():
    """Test basic ModelBuilder functionality."""
    model = (ModelBuilder("test_model")
             .set_rx_num(1)
             .add_channel(BipolarChannel(
                 channel_id=1,
                 device_path="/dev/input/js0",
                 control_code="0",
                 device_name="Joystick",
                 control_name="X"
             ))
             .build())
    
    assert model.name == "test_model"
    assert model.rx_num == 1
    assert len(model.channels) == 1
    assert 1 in model.channels
    assert model.channels[1].control_type == "bipolar"
    assert model.channels[1].device_path == "/dev/input/js0"


def test_model_builder_multiple_channels():
    """Test adding multiple channels."""
    ch1 = BipolarChannel(1, "/dev/input/js0", "0", "Joystick", "X")
    ch2 = BipolarChannel(2, "/dev/input/js0", "1", "Joystick", "Y")
    ch3 = VirtualChannel(3, "virtual-ch")
    
    model = (ModelBuilder("multi_channel")
             .add_channels(ch1, ch2, ch3)
             .build())
    
    assert len(model.channels) == 3
    assert model.channels[1].control_type == "bipolar"
    assert model.channels[2].control_type == "bipolar"
    assert model.channels[3].control_type == "unipolar"
    assert model.channels[3].control_code == "virtual"


def test_model_builder_with_processors():
    """Test adding processors to model."""
    model = (ModelBuilder("proc_model")
             .add_channel(BipolarChannel(1, "/dev/input/js0", "0"))
             .add_channel(BipolarChannel(2, "/dev/input/js0", "1"))
             .add_processor(ReverseProcessor(channels={1: True, 2: False}))
             .add_processor(EndpointProcessor(endpoints={1: (-0.8, 0.9)}))
             .build())
    
    assert "reverse" in model.processors
    assert "endpoints" in model.processors
    assert model.processors["reverse"]["ch1"] is True
    assert model.processors["reverse"]["ch2"] is False
    assert model.processors["endpoints"]["ch1"]["min"] == -0.8


def test_model_builder_rx_num_clamping():
    """Test that rx_num is clamped to 0-15 range."""
    model1 = ModelBuilder("test1").set_rx_num(-5).build()
    assert model1.rx_num == 0
    
    model2 = ModelBuilder("test2").set_rx_num(20).build()
    assert model2.rx_num == 15
    
    model3 = ModelBuilder("test3").set_rx_num(7).build()
    assert model3.rx_num == 7


def test_model_builder_model_id():
    """Test setting custom model_id."""
    model = (ModelBuilder("test")
             .set_model_id("custom_id_12345")
             .build())
    
    assert model.model_id == "custom_id_12345"


def test_model_builder_auto_model_id():
    """Test that model_id is auto-generated if not set."""
    model = ModelBuilder("test").build()
    
    # Should have a model_id (generated)
    assert model.model_id is not None
    assert len(model.model_id) > 0


def test_model_builder_bind_timestamp():
    """Test setting bind timestamp."""
    model = (ModelBuilder("test")
             .set_bind_timestamp("2024-01-01T00:00:00")
             .build())
    
    assert model.bind_timestamp == "2024-01-01T00:00:00"


def test_model_builder_from_model():
    """Test creating builder from existing Model."""
    # Create a model the normal way
    original = (ModelBuilder("original")
                .set_rx_num(3)
                .set_model_id("test_id")
                .add_channel(BipolarChannel(1, "/dev/input/js0", "0", "JS", "X"))
                .add_channel(VirtualChannel(2, "virtual"))
                .add_processor(ReverseProcessor(channels={1: True}))
                .build())
    
    # Create a builder from it
    builder = ModelBuilder.from_model(original)
    rebuilt = builder.build()
    
    # Should be identical
    assert rebuilt.name == original.name
    assert rebuilt.rx_num == original.rx_num
    assert rebuilt.model_id == original.model_id
    assert len(rebuilt.channels) == len(original.channels)
    assert rebuilt.channels[1].control_type == original.channels[1].control_type
    assert rebuilt.channels[2].control_code == "virtual"
    assert "reverse" in rebuilt.processors


def test_model_builder_modify_existing():
    """Test modifying an existing model via from_model."""
    original = (ModelBuilder("original")
                .set_rx_num(1)
                .add_channel(BipolarChannel(1, "/dev/input/js0", "0"))
                .build())
    
    # Modify via builder
    modified = (ModelBuilder.from_model(original)
                .set_rx_num(2)
                .add_channel(BipolarChannel(3, "/dev/input/js0", "1"))
                .build())
    
    assert modified.rx_num == 2
    assert len(modified.channels) == 2  # Added a new channel
    assert 1 in modified.channels
    assert 3 in modified.channels


def test_model_builder_differential_processor():
    """Test adding differential processor."""
    model = (ModelBuilder("diff_model")
             .add_channel(BipolarChannel(1, "/dev/input/js0", "0"))
             .add_channel(BipolarChannel(2, "/dev/input/js0", "1"))
             .add_processor(DifferentialProcessor(mixes=[
                 DifferentialMix(left=2, right=1, inverse=True)
             ]))
             .build())
    
    assert "differential" in model.processors
    assert len(model.processors["differential"]) == 1
    assert model.processors["differential"][0]["left"] == "ch2"
    assert model.processors["differential"][0]["right"] == "ch1"
    assert model.processors["differential"][0]["inverse"] is True


def test_model_builder_empty():
    """Test building an empty model."""
    model = ModelBuilder("empty").build()
    
    assert model.name == "empty"
    assert len(model.channels) == 0
    assert model.processors == {}
    assert model.rx_num == 0
