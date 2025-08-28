# pi-tx

## KivyMD UI

A simple KivyMD interface is provided to:

1. Select a model from `models/` (JSON files)  
2. Display each configured channel (CH_1 .. CH_N) with its live value  
3. Update values in real time as joystick inputs change

### Run the UI

```
python -m pip install -r requirements.txt
python src/main_md.py
```

Click "Select Model" to pick from existing model JSON files. The chosen model is copied to `model_mapping.json` (used by the input system). Channel labels update automatically when inputs change.

### Adding / Editing Models

Create or modify JSON files in `models/` (or use the existing CLI tooling) then restart / refresh (toolbar refresh icon) to see them in the menu.

### Notes

* Channel values are normalized to the ranges defined in control mappings.
* Only channels defined in the selected model are displayed.
* Selecting a model reinitializes control callbacks based on `model_mapping.json`.
