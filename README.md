# pi-tx

Low‑latency joystick → channel mapper with a KivyMD UI for selecting "models" (channel layouts) and visualizing live channel values.

## Features

- Model selection from JSON files in `models/`
- Live channel bars (bipolar, unipolar, button) with color coding
- Queue‑based input pipeline (reduced UI thread overhead)
- Automatic persistence of last selected model (`.last_model`)
- Pluggable stick/control mapping file (`pi_tx/input/mappings/stick_mapping.json`)

## Quick Start

```bash
python -m pip install -r requirements.txt
python -m pi_tx        # launches the UI
```

If you run `python pi_tx/main.py` directly you may hit relative‑import issues; prefer `-m` which loads the package properly.

## Directory Layout (core parts)

```
pi_tx/
	config/           # central paths & constants
	domain/           # model + channel domain abstractions
	infrastructure/   # persistence helpers (e.g. last model)
	input/            # InputController + mappings/
		mappings/
			stick_mapping.json  # per‑device control definitions
	ui/               # KivyMD GUI (create_gui)
	app.py            # run() helper
	main.py / __main__.py  # entry points
models/             # user model JSON files (channel layouts)
```

## Models

A model file (e.g. `models/cat_d6t.json`) looks like:

```json
{
	"name": "cat_d6t",
	"channels": {
		"1": {"device_path": "/dev/input/event14", "control_code": 1, "control_type": "bipolar"}
	}
}
```

Fields:
- `device_path`: Linux evdev device path
- `control_code`: numeric event code within that device
- `control_type`: `bipolar` | `unipolar` | `button`

Add more numbered entries as needed. Omitted channels simply don't render.

## Stick Mapping File

`pi_tx/input/mappings/stick_mapping.json` describes raw device capabilities (axis ranges, fuzz/flat) used for normalization.

If you currently have a mapping at repository root (`stick_mapping.json`), move/copy it to the path above so the default `InputController` finds it. Or pass an explicit path:

```python
from pi_tx.input.controls import InputController
ic = InputController(mapping_file="./stick_mapping.json")
```

## Running With Debug Logging

```python
from pi_tx.app import run
from pi_tx.input.controls import InputController

ic = InputController(debug=True)
# then pass into GUI factory if embedding
```

## Creating / Editing Models

1. Duplicate an existing JSON file in `models/`
2. Adjust channel mappings (ensure the `device_path` and `control_code` exist in your stick mapping file)
3. Start the app and choose the model from the toolbar menu (refresh icon rescans)
4. The last chosen model is stored in `.last_model`

## Architecture Overview

Layered (lightweight):
- input: hardware event capture & normalization (evdev → queue)
- domain: ModelRepository (loads channel layout), ChannelStore (state + listeners)
- ui: visual layer drains queue each frame, updates bars
- infrastructure: persistence utilities
- config: path constants, separation from logic

## Roadmap Ideas

- Console entry point (`pi-tx`) via `setup.cfg` / `pyproject.toml`
- Hot‑plug device detection
- Model edit UI
- Network transmission of channel values

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No devices detected | Confirm permissions: run with access to `/dev/input/event*` (udev rule or sudo) |
| Values stuck at 0   | Ensure `device_path` & `control_code` match those in stick mapping |
| ImportError on run  | Use `python -m pi_tx` instead of file path |

## License

MIT (add explicit LICENSE file if distributing)

