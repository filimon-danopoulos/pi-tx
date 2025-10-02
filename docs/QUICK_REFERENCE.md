# Python Model API Quick Reference

## Import Statements

```python
from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.channel import (
    BipolarChannel, UnipolarChannel, ButtonChannel,
    LatchingButtonChannel, VirtualChannel
)
from pi_tx.domain.processors import (
    ReverseProcessor, EndpointProcessor,
    DifferentialProcessor, DifferentialMix,
    AggregateProcessor, AggregateMix, AggregateChannel
)
```

## Channel Types

| Type | Range | Use Case |
|------|-------|----------|
| `BipolarChannel` | -1.0 to 1.0 | Joystick axes, analog sticks |
| `UnipolarChannel` | 0.0 to 1.0 | Throttles, sliders |
| `ButtonChannel` | 0.0 or 1.0 | Momentary buttons |
| `LatchingButtonChannel` | 0.0 or 1.0 | Toggle switches |
| `VirtualChannel` | Configurable | Computed values |

## Channel Creation

```python
# Bipolar channel (joystick axis)
BipolarChannel(
    channel_id=1,
    device_path="/dev/input/js0",
    control_code="0",
    device_name="Joystick",    # Optional
    control_name="X-axis"       # Optional
)

# Virtual channel (not tied to input)
VirtualChannel(
    channel_id=7,
    control_name="mix-output",
    control_type="unipolar"     # or "bipolar", "button"
)
```

## Processor Types

### Reverse Processor
```python
ReverseProcessor(channels={
    1: True,   # Reverse channel 1
    2: False,  # Don't reverse channel 2
})
```

### Endpoint Processor
```python
EndpointProcessor(endpoints={
    1: (-0.8, 0.9),   # Clamp ch1: -0.8 to 0.9
    2: (0.0, 1.0),    # Clamp ch2: 0.0 to 1.0
})
```

### Differential Processor
```python
DifferentialProcessor(mixes=[
    DifferentialMix(
        left=2,          # Left input channel
        right=1,         # Right input channel
        inverse=True     # Swap outputs
    )
])
```

### Aggregate Processor
```python
AggregateProcessor(mixes=[
    AggregateMix(
        channels=[
            AggregateChannel(channel_id=1, weight=0.5),
            AggregateChannel(channel_id=2, weight=0.5),
        ],
        target=7  # Output to channel 7
    )
])
```

## Building Models

### Direct Method
```python
model = (ModelBuilder("my_model")
    .set_rx_num(1)
    .add_channel(BipolarChannel(1, "/dev/input/js0", "0"))
    .add_processor(ReverseProcessor({1: True}))
    .build())
```

### Class-Based Method
```python
class MyModel:
    def __init__(self):
        self.name = "my_model"
        self.rx_num = 1
    
    def create_channels(self):
        return [
            BipolarChannel(1, "/dev/input/js0", "0"),
            BipolarChannel(2, "/dev/input/js0", "1"),
        ]
    
    def create_processors(self):
        return [ReverseProcessor({1: True})]
    
    def build(self):
        builder = ModelBuilder(self.name)
        builder.set_rx_num(self.rx_num)
        for ch in self.create_channels():
            builder.add_channel(ch)
        for proc in self.create_processors():
            builder.add_processor(proc)
        return builder.build()
```

## Modifying Existing Models

```python
# Load a model
repo = ModelRepository()
original = repo.load_model("existing_model")

# Modify it
modified = (ModelBuilder.from_model(original)
    .set_rx_num(3)
    .add_channel(VirtualChannel(8, "extra"))
    .build())

# Save it
repo.save_model(modified)
```

## Subclassing

```python
class BaseModel:
    DEVICE_PATH = "/dev/input/js0"
    
    def build(self):
        return (ModelBuilder(self.name)
            .add_channel(BipolarChannel(1, self.DEVICE_PATH, "0"))
            .build())

class CustomModel(BaseModel):
    DEVICE_PATH = "/dev/input/by-id/custom-joystick"
```

## Common Patterns

### Add Multiple Channels
```python
builder.add_channels(
    BipolarChannel(1, "/dev/js0", "0"),
    BipolarChannel(2, "/dev/js0", "1"),
    VirtualChannel(3, "output")
)
```

### Set Model Metadata
```python
builder.set_model_id("custom_id_123")
builder.set_bind_timestamp("2024-01-01T00:00:00")
```

### Tank Steering Setup
```python
# Left stick Y (ch1) + Right stick Y (ch2) -> differential
.add_processor(DifferentialProcessor(mixes=[
    DifferentialMix(left=2, right=1, inverse=False)
]))
```

### Sound Mix from Multiple Channels
```python
.add_processor(AggregateProcessor(mixes=[
    AggregateMix(
        channels=[
            AggregateChannel(1, 0.25),  # 25% from ch1
            AggregateChannel(2, 0.25),  # 25% from ch2
            AggregateChannel(3, 0.5),   # 50% from ch3
        ],
        target=7  # Output to ch7
    )
]))
```

## See Also

- **Full Documentation**: `docs/PYTHON_MODEL_GUIDE.md`
- **Examples**: `examples/model_definitions.py`
- **Demo Script**: `examples/demo_models.py`
- **Tests**: `tests/test_model_builder.py`, `tests/test_integration.py`
