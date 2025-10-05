# New UI for pi-tx

This is a simplified UI that uses the new Python class-based model system.

## Features

- Loads the `cat_d6t` model (hardcoded)
- Displays live channel values updated at 30Hz
- Uses the model's `listen()` method to gather input asynchronously
- Uses the model's `readValues()` method to get processed channel values

## Usage

```bash
python ui/main.py
```

Or from the project root:

```bash
python -m ui.main
```

## Architecture

- **No JSON files**: Uses Python class-based models from `examples/cat_d6t_example.py`
- **No old GUI logic**: Completely separate from the `gui/` folder
- **Async input handling**: `model.listen()` runs in a background thread
- **30Hz updates**: `model.readValues()` called every ~33ms to refresh the display

## Requirements

- Kivy (for the GUI)
- evdev (for input device handling)
- All dependencies from main project (see `requirements.txt`)

## Structure

```
ui/
├── __init__.py       # Package marker
├── main.py           # Main UI application
└── README.md         # This file
```

## Key Differences from Old GUI

1. **No JSON loading**: Model is imported directly from Python code
2. **Simpler architecture**: No model manager, persistence, or file cache
3. **Direct model interaction**: Calls `model.listen()` and `model.readValues()` directly
4. **Read-only**: Just displays values, no configuration or model editing
