"""Integration test for Python-based model creation and usage."""
import pytest
import tempfile
import json
from pathlib import Path

from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.model_repo import ModelRepository
from pi_tx.domain.channel import BipolarChannel, VirtualChannel
from pi_tx.domain.processors import ReverseProcessor, AggregateProcessor, AggregateMix, AggregateChannel
from examples.model_definitions import D6TModel, SimpleModel


def test_python_model_to_json_roundtrip(tmp_path):
    """Test that a Python-built model can be saved to JSON and loaded back."""
    repo = ModelRepository(str(tmp_path))
    
    # Build a model in Python
    model = (ModelBuilder("test_roundtrip")
             .set_rx_num(3)
             .add_channel(BipolarChannel(1, "/dev/input/js0", "0", "Stick", "X"))
             .add_channel(BipolarChannel(2, "/dev/input/js0", "1", "Stick", "Y"))
             .add_processor(ReverseProcessor(channels={1: True}))
             .build())
    
    # Save it
    repo.save_model(model)
    
    # Load it back
    loaded = repo.load_model("test_roundtrip")
    
    # Verify it matches
    assert loaded.name == model.name
    assert loaded.rx_num == model.rx_num
    assert len(loaded.channels) == len(model.channels)
    assert loaded.channels[1].control_type == "bipolar"
    assert loaded.channels[2].control_type == "bipolar"
    assert "reverse" in loaded.processors
    assert loaded.processors["reverse"]["ch1"] is True


def test_d6t_model_json_equivalence(tmp_path):
    """Test that D6TModel produces equivalent JSON to the original."""
    repo = ModelRepository(str(tmp_path))
    
    # Build D6T model from Python
    python_model = D6TModel().build()
    
    # Save it to JSON
    repo.save_model(python_model)
    
    # Load it back
    loaded = repo.load_model("cat_d6t")
    
    # Verify key attributes match
    assert loaded.name == "cat_d6t"
    assert loaded.rx_num == 1
    assert len(loaded.channels) == 7
    assert "reverse" in loaded.processors
    assert "endpoints" in loaded.processors
    assert "differential" in loaded.processors
    assert "aggregate" in loaded.processors


def test_model_builder_from_json_model(tmp_path):
    """Test that we can load a JSON model and modify it with ModelBuilder."""
    repo = ModelRepository(str(tmp_path))
    
    # Create and save a simple JSON model
    simple_model = SimpleModel("base").build()
    repo.save_model(simple_model)
    
    # Load it
    loaded = repo.load_model("base")
    
    # Modify it using ModelBuilder
    modified = (ModelBuilder.from_model(loaded)
                .set_rx_num(5)
                .add_channel(VirtualChannel(3, "extra"))
                .add_processor(AggregateProcessor(mixes=[
                    AggregateMix(
                        channels=[AggregateChannel(1, 0.5), AggregateChannel(2, 0.5)],
                        target=3
                    )
                ]))
                .build())
    
    # Save the modified version
    repo.save_model(modified)
    
    # Load it back and verify modifications
    reloaded = repo.load_model("base")
    assert reloaded.rx_num == 5
    assert len(reloaded.channels) == 3
    assert "aggregate" in reloaded.processors


def test_json_and_python_models_coexist(tmp_path):
    """Test that JSON and Python models can coexist in the repository."""
    repo = ModelRepository(str(tmp_path))
    
    # Create a JSON model manually
    json_model_path = tmp_path / "json_model.json"
    json_data = {
        "name": "json_model",
        "rx_num": 2,
        "channels": {
            "ch1": {"control_type": "unipolar", "device_path": "", "control_code": "0"}
        },
        "processors": {}
    }
    with open(json_model_path, 'w') as f:
        json.dump(json_data, f)
    
    # Create a Python model
    python_model = SimpleModel("python_model").build()
    repo.save_model(python_model)
    
    # List models - should see both
    models = repo.list_models()
    assert "json_model" in models
    assert "python_model" in models
    
    # Load both
    json_loaded = repo.load_model("json_model")
    python_loaded = repo.load_model("python_model")
    
    assert json_loaded.name == "json_model"
    assert python_loaded.name == "python_model"


def test_complex_processor_roundtrip(tmp_path):
    """Test that complex processor configurations survive JSON roundtrip."""
    repo = ModelRepository(str(tmp_path))
    
    from pi_tx.domain.processors import (
        EndpointProcessor, DifferentialProcessor, DifferentialMix
    )
    
    # Build a model with all processor types
    model = (ModelBuilder("complex")
             .add_channel(BipolarChannel(1, "/dev/js0", "0"))
             .add_channel(BipolarChannel(2, "/dev/js0", "1"))
             .add_channel(BipolarChannel(3, "/dev/js0", "2"))
             .add_channel(VirtualChannel(4, "agg"))
             .add_processor(ReverseProcessor(channels={1: True, 2: False}))
             .add_processor(EndpointProcessor(endpoints={1: (-0.8, 0.9)}))
             .add_processor(DifferentialProcessor(mixes=[
                 DifferentialMix(left=2, right=1, inverse=True)
             ]))
             .add_processor(AggregateProcessor(mixes=[
                 AggregateMix(
                     channels=[AggregateChannel(1, 0.3), AggregateChannel(2, 0.7)],
                     target=4
                 )
             ]))
             .build())
    
    # Save and reload
    repo.save_model(model)
    loaded = repo.load_model("complex")
    
    # Verify all processors are present and configured correctly
    assert "reverse" in loaded.processors
    assert loaded.processors["reverse"]["ch1"] is True
    assert loaded.processors["reverse"]["ch2"] is False
    
    assert "endpoints" in loaded.processors
    assert loaded.processors["endpoints"]["ch1"]["min"] == -0.8
    assert loaded.processors["endpoints"]["ch1"]["max"] == 0.9
    
    assert "differential" in loaded.processors
    assert len(loaded.processors["differential"]) == 1
    assert loaded.processors["differential"][0]["inverse"] is True
    
    assert "aggregate" in loaded.processors
    assert len(loaded.processors["aggregate"]) == 1
    assert loaded.processors["aggregate"][0]["target"] == "ch4"
