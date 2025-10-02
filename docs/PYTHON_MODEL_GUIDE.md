# Python-Based Model Configuration Guide

This guide explains how to define RC transmitter models using Python classes instead of JSON files.

## Overview

The pi-tx system now supports defining models entirely in Python code. This approach offers several advantages over JSON files:

- **Type safety**: Python's type system helps catch errors at development time
- **Code reuse**: Inherit from base classes and share configuration
- **Flexibility**: Use Python's full expressiveness for complex configurations
- **IDE support**: Autocomplete, refactoring, and inline documentation
- **Maintainability**: Easier to manage and version control

## Core Components

### 1. Channels

Channels represent individual control inputs (sticks, buttons, etc.). There are several channel types:

#### `BipolarChannel`
Values range from -1.0 to 1.0. Used for joystick axes, analog sticks.

```python
from pi_tx.domain.channel import BipolarChannel

channel = BipolarChannel(
    channel_id=1,
    device_path="/dev/input/js0",
    control_code="0",
    device_name="Joystick",
    control_name="X-axis"
)
```

#### `UnipolarChannel`
Values range from 0.0 to 1.0. Used for throttles, sliders, potentiometers.

```python
from pi_tx.domain.channel import UnipolarChannel

channel = UnipolarChannel(
    channel_id=2,
    device_path="/dev/input/js0",
    control_code="2",
    device_name="Joystick",
    control_name="Throttle"
)
```

#### `ButtonChannel`
Momentary button (0.0 when released, 1.0 when pressed).

```python
from pi_tx.domain.channel import ButtonChannel

channel = ButtonChannel(
    channel_id=3,
    device_path="/dev/input/js0",
    control_code="288",
    device_name="Joystick",
    control_name="Trigger"
)
```

#### `LatchingButtonChannel`
Latching button that toggles between 0.0 and 1.0 on each press.

```python
from pi_tx.domain.channel import LatchingButtonChannel

channel = LatchingButtonChannel(
    channel_id=4,
    device_path="/dev/input/js0",
    control_code="289",
    device_name="Joystick",
    control_name="Mode-Switch"
)
```

#### `VirtualChannel`
Virtual channel not tied to physical input, useful for computed values.

```python
from pi_tx.domain.channel import VirtualChannel

channel = VirtualChannel(
    channel_id=5,
    control_name="sound-mix",
    control_type="unipolar"
)
```

### 2. Processors

Processors transform channel values through various operations:

#### `ReverseProcessor`
Reverses the polarity of specified channels.

```python
from pi_tx.domain.processors import ReverseProcessor

processor = ReverseProcessor(channels={
    1: True,   # Reverse channel 1
    2: False,  # Don't reverse channel 2
    3: True,   # Reverse channel 3
})
```

#### `EndpointProcessor`
Clamps channel values to custom min/max ranges.

```python
from pi_tx.domain.processors import EndpointProcessor

processor = EndpointProcessor(endpoints={
    1: (-0.80, 0.90),  # Channel 1: -0.8 to 0.9
    2: (-1.00, 1.00),  # Channel 2: -1.0 to 1.0
    3: (0.00, 1.00),   # Channel 3: 0.0 to 1.0
})
```

#### `DifferentialProcessor`
Applies differential mixing to channel pairs (useful for tank steering).

```python
from pi_tx.domain.processors import DifferentialProcessor, DifferentialMix

processor = DifferentialProcessor(mixes=[
    DifferentialMix(left=2, right=1, inverse=True),
    DifferentialMix(left=4, right=3, inverse=False),
])
```

Differential mixing computes:
- `left_out = left + right`
- `right_out = right - left`

If `inverse=True`, the outputs are swapped.

#### `AggregateProcessor`
Aggregates multiple channels into a single output channel.

```python
from pi_tx.domain.processors import (
    AggregateProcessor, 
    AggregateMix, 
    AggregateChannel
)

processor = AggregateProcessor(mixes=[
    AggregateMix(
        channels=[
            AggregateChannel(channel_id=1, weight=0.2),
            AggregateChannel(channel_id=2, weight=0.2),
            AggregateChannel(channel_id=3, weight=0.4),
            AggregateChannel(channel_id=4, weight=0.4),
        ],
        target=7  # Write result to channel 7
    )
])
```

### 3. ModelBuilder

The `ModelBuilder` provides a fluent API for constructing models:

```python
from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.channel import BipolarChannel
from pi_tx.domain.processors import ReverseProcessor

model = (ModelBuilder("my_model")
    .set_rx_num(1)
    .add_channel(BipolarChannel(1, "/dev/input/js0", "0", "Stick", "X"))
    .add_channel(BipolarChannel(2, "/dev/input/js0", "1", "Stick", "Y"))
    .add_processor(ReverseProcessor({1: True}))
    .build())
```

## Creating a Model Definition

There are two approaches to defining models:

### Approach 1: Direct ModelBuilder Usage

Simple models can be built directly:

```python
from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.channel import BipolarChannel

def create_simple_model():
    return (ModelBuilder("simple_model")
        .set_rx_num(0)
        .add_channel(BipolarChannel(1, "/dev/input/js0", "0", "JS", "X"))
        .add_channel(BipolarChannel(2, "/dev/input/js0", "1", "JS", "Y"))
        .build())

model = create_simple_model()
```

### Approach 2: Model Definition Classes

For complex models or reusable configurations, create a class:

```python
from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.channel import BipolarChannel, VirtualChannel
from pi_tx.domain.processors import (
    ReverseProcessor,
    EndpointProcessor,
    AggregateProcessor,
    AggregateMix,
    AggregateChannel,
)

class MyModel:
    """Custom model definition."""
    
    def __init__(self):
        self.name = "my_model"
        self.rx_num = 1
    
    def create_channels(self):
        """Define channels."""
        return [
            BipolarChannel(1, "/dev/input/js0", "0", "Stick", "X"),
            BipolarChannel(2, "/dev/input/js0", "1", "Stick", "Y"),
            VirtualChannel(3, "virtual-out"),
        ]
    
    def create_processors(self):
        """Define processors."""
        return [
            ReverseProcessor(channels={1: True}),
            EndpointProcessor(endpoints={1: (-0.8, 0.9)}),
            AggregateProcessor(mixes=[
                AggregateMix(
                    channels=[
                        AggregateChannel(1, 0.5),
                        AggregateChannel(2, 0.5),
                    ],
                    target=3
                )
            ]),
        ]
    
    def build(self):
        """Build the model."""
        builder = ModelBuilder(self.name)
        builder.set_rx_num(self.rx_num)
        
        for channel in self.create_channels():
            builder.add_channel(channel)
        
        for processor in self.create_processors():
            builder.add_processor(processor)
        
        return builder.build()

# Create an instance
model = MyModel().build()
```

## Subclassing and Customization

Model definition classes can be subclassed for variations:

```python
class BaseModel:
    DEVICE_PATH = "/dev/input/js0"
    
    def __init__(self):
        self.name = "base_model"
        self.rx_num = 0
    
    def create_channels(self):
        return [
            BipolarChannel(1, self.DEVICE_PATH, "0", "Stick", "X"),
            BipolarChannel(2, self.DEVICE_PATH, "1", "Stick", "Y"),
        ]
    
    def build(self):
        builder = ModelBuilder(self.name)
        builder.set_rx_num(self.rx_num)
        for channel in self.create_channels():
            builder.add_channel(channel)
        return builder.build()

class CustomModel(BaseModel):
    """Customized variant with different device."""
    
    DEVICE_PATH = "/dev/input/by-id/usb-Custom_Stick-event-joystick"
    
    def __init__(self):
        super().__init__()
        self.name = "custom_model"
        self.rx_num = 2

# Use the customized variant
model = CustomModel().build()
```

## Complete Example: D6T Model

See `examples/model_definitions.py` for a complete example based on the cat_d6t.json file:

```python
from examples.model_definitions import D6TModel

# Create the D6T model
model = D6TModel().build()

# Subclass for customization
class MyD6T(D6TModel):
    def __init__(self):
        super().__init__()
        self.name = "my_d6t"
        self.rx_num = 3

my_model = MyD6T().build()
```

## Using Models in Your Application

Once a model is built, it can be used with the existing model repository:

```python
from pi_tx.domain.model_repo import ModelRepository
from examples.model_definitions import D6TModel

# Build the model
model = D6TModel().build()

# Save it
repo = ModelRepository()
repo.save_model(model)

# Load it later
loaded = repo.load_model("cat_d6t")
```

## Migration from JSON

To migrate an existing JSON model to Python:

1. **Study the JSON structure**: Look at channels and processors
2. **Create a model class**: Use the pattern shown above
3. **Define channels**: Convert each JSON channel to a Channel instance
4. **Define processors**: Convert each processor section to Processor instances
5. **Test**: Build the model and compare the output with the JSON version

Example migration:

**Before (JSON):**
```json
{
  "name": "simple",
  "rx_num": 1,
  "channels": {
    "ch1": {
      "control_type": "bipolar",
      "device_path": "/dev/input/js0",
      "control_code": "0"
    }
  },
  "processors": {
    "reverse": {
      "ch1": true
    }
  }
}
```

**After (Python):**
```python
class SimpleModel:
    def build(self):
        return (ModelBuilder("simple")
            .set_rx_num(1)
            .add_channel(BipolarChannel(1, "/dev/input/js0", "0"))
            .add_processor(ReverseProcessor({1: True}))
            .build())
```

## Best Practices

1. **Use descriptive names**: Make channel and control names clear
2. **Group related configuration**: Keep channels and processors together
3. **Leverage inheritance**: Create base classes for common patterns
4. **Add docstrings**: Document what each model does
5. **Test thoroughly**: Write tests for your model definitions
6. **Version control**: Python files are easier to diff and merge than JSON

## Backward Compatibility

The new Python-based approach is fully compatible with JSON files. The system continues to:
- Load models from JSON files via `ModelRepository`
- Parse JSON using `parse_model_dict()`
- Save models back to JSON format

You can gradually migrate models from JSON to Python at your own pace.
