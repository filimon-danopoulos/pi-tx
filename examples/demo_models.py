#!/usr/bin/env python3
"""Demonstration script for Python-based model definitions.

This script shows various ways to create and use models with the new
Python API instead of JSON files.
"""

from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.model_json import Model
from pi_tx.domain.channel import (
    BipolarChannel,
    UnipolarChannel,
    ButtonChannel,
    VirtualChannel,
)
from pi_tx.domain.processors import (
    ReverseProcessor,
    EndpointProcessor,
    DifferentialProcessor,
    DifferentialMix,
    AggregateProcessor,
    AggregateMix,
    AggregateChannel,
)
from examples.model_definitions import D6TModel, SimpleModel, CustomD6TModel


def demo_simple_builder():
    """Demonstrate simple model building with ModelBuilder."""
    print("\n" + "="*60)
    print("DEMO 1: Simple ModelBuilder Usage")
    print("="*60)
    
    model = (ModelBuilder("demo_simple")
             .set_rx_num(1)
             .add_channel(BipolarChannel(
                 channel_id=1,
                 device_path="/dev/input/js0",
                 control_code="0",
                 device_name="Joystick",
                 control_name="X-axis"
             ))
             .add_channel(BipolarChannel(
                 channel_id=2,
                 device_path="/dev/input/js0",
                 control_code="1",
                 device_name="Joystick",
                 control_name="Y-axis"
             ))
             .add_processor(ReverseProcessor(channels={1: True}))
             .build())
    
    print(f"Model name: {model.name}")
    print(f"RX number: {model.rx_num}")
    print(f"Channels: {len(model.channels)}")
    print(f"Processors: {list(model.processors.keys())}")
    for ch_id, ch in model.channels.items():
        print(f"  Ch{ch_id}: {ch.control_type} - {ch.control_name}")


def demo_model_class():
    """Demonstrate defining a model as a class."""
    print("\n" + "="*60)
    print("DEMO 2: Model Definition Class")
    print("="*60)
    
    class QuadcopterModel:
        """4-channel model for a quadcopter."""
        
        def __init__(self):
            self.name = "quadcopter"
            self.rx_num = 0
        
        def create_channels(self):
            return [
                BipolarChannel(1, "/dev/input/js0", "1", "Stick", "Pitch"),
                BipolarChannel(2, "/dev/input/js0", "0", "Stick", "Roll"),
                UnipolarChannel(3, "/dev/input/js0", "2", "Stick", "Throttle"),
                BipolarChannel(4, "/dev/input/js0", "5", "Stick", "Yaw"),
            ]
        
        def create_processors(self):
            return [
                ReverseProcessor(channels={1: True}),
                EndpointProcessor(endpoints={3: (0.0, 1.0)}),
            ]
        
        def build(self):
            builder = ModelBuilder(self.name)
            builder.set_rx_num(self.rx_num)
            for ch in self.create_channels():
                builder.add_channel(ch)
            for proc in self.create_processors():
                builder.add_processor(proc)
            return builder.build()
    
    model = QuadcopterModel().build()
    
    print(f"Model name: {model.name}")
    print(f"Channels: {len(model.channels)}")
    for ch_id, ch in sorted(model.channels.items()):
        print(f"  Ch{ch_id}: {ch.control_type} - {ch.control_name}")
    print(f"Processors: {list(model.processors.keys())}")


def demo_processors():
    """Demonstrate various processor types."""
    print("\n" + "="*60)
    print("DEMO 3: Using Processors")
    print("="*60)
    
    model = (ModelBuilder("demo_processors")
             .add_channel(BipolarChannel(1, "/dev/input/js0", "0", "JS", "Left-X"))
             .add_channel(BipolarChannel(2, "/dev/input/js0", "1", "JS", "Left-Y"))
             .add_channel(BipolarChannel(3, "/dev/input/js0", "2", "JS", "Right-X"))
             .add_channel(BipolarChannel(4, "/dev/input/js0", "3", "JS", "Right-Y"))
             .add_channel(VirtualChannel(5, "aggregate-out"))
             # Reverse channels 1 and 3
             .add_processor(ReverseProcessor(channels={1: True, 3: True}))
             # Limit channel 2 range
             .add_processor(EndpointProcessor(endpoints={2: (-0.8, 0.9)}))
             # Differential mixing on channels 1 and 2
             .add_processor(DifferentialProcessor(mixes=[
                 DifferentialMix(left=2, right=1, inverse=False)
             ]))
             # Aggregate all channels into channel 5
             .add_processor(AggregateProcessor(mixes=[
                 AggregateMix(
                     channels=[
                         AggregateChannel(1, 0.25),
                         AggregateChannel(2, 0.25),
                         AggregateChannel(3, 0.25),
                         AggregateChannel(4, 0.25),
                     ],
                     target=5
                 )
             ]))
             .build())
    
    print(f"Model: {model.name}")
    print("\nProcessors configured:")
    for proc_type, proc_data in model.processors.items():
        print(f"  - {proc_type}")
    
    print("\nReverse configuration:")
    for ch, rev in model.processors['reverse'].items():
        if rev:
            print(f"  {ch}: reversed")
    
    print("\nEndpoint configuration:")
    for ch, ep in model.processors['endpoints'].items():
        print(f"  {ch}: min={ep['min']}, max={ep['max']}")


def demo_virtual_channels():
    """Demonstrate virtual channels."""
    print("\n" + "="*60)
    print("DEMO 4: Virtual Channels")
    print("="*60)
    
    model = (ModelBuilder("demo_virtual")
             .add_channel(BipolarChannel(1, "/dev/input/js0", "0", "JS", "X"))
             .add_channel(BipolarChannel(2, "/dev/input/js0", "1", "JS", "Y"))
             .add_channel(VirtualChannel(3, "computed-mix", "unipolar"))
             .add_channel(VirtualChannel(4, "status-flag", "button"))
             .add_processor(AggregateProcessor(mixes=[
                 AggregateMix(
                     channels=[AggregateChannel(1, 0.5), AggregateChannel(2, 0.5)],
                     target=3
                 )
             ]))
             .build())
    
    print(f"Model: {model.name}")
    print("\nChannels:")
    for ch_id, ch in sorted(model.channels.items()):
        is_virtual = ch.control_code == "virtual"
        print(f"  Ch{ch_id}: {ch.control_type} - {ch.control_name} "
              f"{'(virtual)' if is_virtual else ''}")


def demo_d6t_model():
    """Demonstrate the D6T model example."""
    print("\n" + "="*60)
    print("DEMO 5: D6T Model (from examples)")
    print("="*60)
    
    model = D6TModel().build()
    
    print(f"Model: {model.name}")
    print(f"Model ID: {model.model_id}")
    print(f"RX Number: {model.rx_num}")
    print(f"Channels: {len(model.channels)}")
    print(f"Processors: {list(model.processors.keys())}")
    
    print("\nChannel summary:")
    for ch_id in sorted(model.channels.keys()):
        ch = model.channels[ch_id]
        is_virtual = ch.control_code == "virtual"
        print(f"  Ch{ch_id}: {ch.control_type:20s} - {ch.control_name:15s} "
              f"{'(virtual)' if is_virtual else ''}")
    
    print("\nDifferential mixes:")
    for mix in model.processors['differential']:
        print(f"  {mix['left']} + {mix['right']} -> differential "
              f"(inverse={mix['inverse']})")


def demo_subclassing():
    """Demonstrate model customization through subclassing."""
    print("\n" + "="*60)
    print("DEMO 6: Model Customization via Subclassing")
    print("="*60)
    
    # Original
    original = D6TModel().build()
    print(f"Original D6T: {original.name}, RX={original.rx_num}, "
          f"channels={len(original.channels)}")
    
    # Customized
    custom = CustomD6TModel().build()
    print(f"Custom D6T:   {custom.name}, RX={custom.rx_num}, "
          f"channels={len(custom.channels)}")
    
    # Show the difference
    new_channels = set(custom.channels.keys()) - set(original.channels.keys())
    if new_channels:
        print(f"\nNew channels in custom model: {new_channels}")
        for ch_id in new_channels:
            ch = custom.channels[ch_id]
            print(f"  Ch{ch_id}: {ch.control_name}")


def demo_modifying_existing():
    """Demonstrate modifying an existing model."""
    print("\n" + "="*60)
    print("DEMO 7: Modifying Existing Models")
    print("="*60)
    
    # Start with simple model
    original = SimpleModel("simple").build()
    print(f"Original: {original.name}, channels={len(original.channels)}")
    
    # Modify it via ModelBuilder.from_model()
    modified = (ModelBuilder.from_model(original)
                .set_rx_num(5)
                .add_channel(VirtualChannel(3, "extra-channel"))
                .add_processor(ReverseProcessor(channels={1: True}))
                .build())
    
    print(f"Modified: {modified.name}, channels={len(modified.channels)}, "
          f"RX={modified.rx_num}")
    print(f"Processors added: {list(modified.processors.keys())}")


def demo_save_to_json():
    """Demonstrate saving a Python model to JSON."""
    print("\n" + "="*60)
    print("DEMO 8: Saving Python Models to JSON")
    print("="*60)
    
    from pi_tx.domain.model_repo import ModelRepository
    import tempfile
    import os
    
    # Create a temporary models directory
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = ModelRepository(tmpdir)
        
        # Build and save a model
        model = SimpleModel("demo_save").build()
        print(f"Saving model: {model.name}")
        repo.save_model(model)
        
        # List models
        models = repo.list_models()
        print(f"Models in repository: {models}")
        
        # Load it back
        loaded = repo.load_model("demo_save")
        print(f"Loaded model: {loaded.name}, channels={len(loaded.channels)}")
        
        # Check JSON file
        json_path = os.path.join(tmpdir, "demo_save.json")
        print(f"JSON file exists: {os.path.exists(json_path)}")


def main():
    """Run all demonstrations."""
    print("\n" + "="*60)
    print("Python-Based Model Configuration Demonstrations")
    print("="*60)
    
    demo_simple_builder()
    demo_model_class()
    demo_processors()
    demo_virtual_channels()
    demo_d6t_model()
    demo_subclassing()
    demo_modifying_existing()
    demo_save_to_json()
    
    print("\n" + "="*60)
    print("All demonstrations complete!")
    print("See docs/PYTHON_MODEL_GUIDE.md for detailed documentation.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
