# Model Definition Examples

This directory contains example model definitions that demonstrate how to create RC transmitter models using Python classes.

## Available Examples

### `D6TModel`

A complete dual-stick model based on the `cat_d6t.json` configuration. Features:

- 7 channels (2 dual-axis sticks + hat + button + virtual)
- Reverse processor for channel polarity
- Endpoint adjustments for fine-tuning ranges
- Differential mixing for tank steering
- Aggregate channel for sound mixing

**Usage:**
```python
from examples.model_definitions import D6TModel

model = D6TModel().build()
```

### `SimpleModel`

A minimal 2-channel model demonstrating the simplest possible configuration.

**Usage:**
```python
from examples.model_definitions import SimpleModel

model = SimpleModel("my_simple_model").build()
```

### `CustomD6TModel`

Demonstrates how to customize an existing model through subclassing. This variant:
- Uses different device paths
- Has a different receiver number
- Adds an extra virtual channel

**Usage:**
```python
from examples.model_definitions import CustomD6TModel

model = CustomD6TModel().build()
```

## Creating Your Own Models

See the [Python Model Guide](../docs/PYTHON_MODEL_GUIDE.md) for detailed instructions on creating your own model definitions.

### Quick Start

1. Import the necessary components:
```python
from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.channel import BipolarChannel
from pi_tx.domain.processors import ReverseProcessor
```

2. Define your model class:
```python
class MyModel:
    def __init__(self):
        self.name = "my_model"
        self.rx_num = 1
    
    def create_channels(self):
        return [
            BipolarChannel(1, "/dev/input/js0", "0", "Stick", "X"),
            BipolarChannel(2, "/dev/input/js0", "1", "Stick", "Y"),
        ]
    
    def create_processors(self):
        return [
            ReverseProcessor({1: True}),
        ]
    
    def build(self):
        builder = ModelBuilder(self.name)
        builder.set_rx_num(self.rx_num)
        for ch in self.create_channels():
            builder.add_channel(ch)
        for proc in self.create_processors():
            builder.add_processor(proc)
        return builder.build()
```

3. Build and use:
```python
model = MyModel().build()
```

## Testing

All example models have corresponding tests in `tests/test_model_definitions.py`. Run them with:

```bash
python -m pytest tests/test_model_definitions.py -v
```

## Saving Models

To save a Python-defined model to JSON format:

```python
from pi_tx.domain.model_repo import ModelRepository

model = D6TModel().build()
repo = ModelRepository()
repo.save_model(model)
```

The model will be saved to `models/cat_d6t.json` and can be loaded later via the repository.
