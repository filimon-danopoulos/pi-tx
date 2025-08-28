"""Interactive tool to create / edit model JSON definitions.

Invoke via:
  python -m pi_tx.tools create-model
"""

from __future__ import annotations
import json
from typing import Dict, Any, List, Tuple, Optional
from pi_tx.config.settings import MODELS_DIR, STICK_MAPPING_FILE


def load_stick_mapping() -> Dict[str, Any]:
    try:
        with open(STICK_MAPPING_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: stick mapping file not found at {STICK_MAPPING_FILE}")
        return {}


def get_available_models() -> List[str]:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return [f.stem for f in MODELS_DIR.glob("*.json")]


def load_existing_model(model_name: str) -> Dict[str, Any]:
    path = MODELS_DIR / f"{model_name}.json"
    if not path.exists():
        return {"name": model_name, "channels": {}}
    with open(path, "r") as f:
        return json.load(f)


def save_model_mapping(mapping: Dict[str, Any], model_name: str) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODELS_DIR / f"{model_name}.json", "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"Saved model to {MODELS_DIR / (model_name + '.json')}")


def get_device_list(stick_mapping: Dict[str, Any]) -> List[Tuple[str, str]]:
    return [(path, info["name"]) for path, info in stick_mapping.items()]


def get_control_list(device_path: str, stick_mapping: Dict[str, Any]):
    device_info = stick_mapping[device_path]
    return list(device_info["controls"].items())


def print_available_controls(stick_mapping: Dict[str, Any]) -> None:
    print("\nAvailable controls by device:")
    for i, (device_path, device_info) in enumerate(stick_mapping.items(), 1):
        print(f"\nDevice {i}: {device_info['name']}")
        print(f"Path: {device_path}")
        print("-" * 70)
        print(f"{'#':<4} {'Control':<25} {'Type':<10} {'Code':<10}")
        print("-" * 70)
        for j, (code, control) in enumerate(device_info["controls"].items(), 1):
            control_type = (
                "Button" if control["event_type"] == 1 else control.get("type", "")
            )
            print(f"{j:<4} {control['name']:<25} {control_type:<10} {code:<10}")


def print_current_model(model_mapping: Dict[str, Any]) -> None:
    print(f"\nModel: {model_mapping.get('name', 'Unnamed')}")
    if not model_mapping["channels"]:
        print("\nNo channels mapped yet.")
        return
    print("\nChannel mapping:")
    print("-" * 90)
    print(f"{'Channel':<10} {'Device':<28} {'Path':<30} {'Control':<15}")
    print("-" * 90)
    for channel, mapping in sorted(
        model_mapping["channels"].items(), key=lambda x: int(x[0])
    ):
        print(
            f"{channel:<10} {mapping.get('device_name','')[:28]:<28} {mapping.get('device_path','')[:30]:<30} {mapping.get('control_name','')[:15]:<15}"
        )


def select_or_create_model() -> Optional[str]:
    while True:
        print("\nModel Selection\n" + "=" * 60)
        models = get_available_models()
        if models:
            print("\nExisting models:")
            for i, m in enumerate(models, 1):
                print(f"{i}. {m}")
        else:
            print("\nNo existing models found.")
        print("\nOptions:\n1. Create new model")
        if models:
            print("2. Load existing model")
        print("0. Exit")
        choice = input("\nEnter choice: ").strip()
        if choice == "0":
            return None
        if choice == "1":
            while True:
                name = input("Enter name: ").strip()
                if not name:
                    print("Name required.")
                    continue
                if name in models:
                    print("Already exists.")
                    continue
                if not name.replace("_", "").isalnum():
                    print("Only letters/numbers/_ allowed.")
                    continue
                return name
        if choice == "2" and models:
            idx = input("Enter model number: ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(models):
                return models[int(idx) - 1]
            print("Invalid index")


def create_mapping() -> None:
    stick_mapping = load_stick_mapping()
    if not stick_mapping:
        return
    model_name = select_or_create_model()
    if not model_name:
        print("Exiting...")
        return
    model_mapping = load_existing_model(model_name)
    while True:
        print("\nModel Mapping Configuration\n" + "=" * 60)
        print_current_model(model_mapping)
        print(
            "\nOptions:\n1. Show controls\n2. Map channel\n3. Remove channel\n4. Save & exit\n5. Exit without saving"
        )
        choice = input("Choose (1-5): ").strip()
        if choice == "1":
            print_available_controls(stick_mapping)
        elif choice == "2":
            channel = input("Channel (1-32): ").strip()
            if not channel.isdigit() or not 1 <= int(channel) <= 32:
                print("Invalid channel")
                continue
            devices = get_device_list(stick_mapping)
            for i, (path, name) in enumerate(devices, 1):
                print(f"{i}. {name}  [{path}]")
            sel = input("Device #: ").strip()
            if not sel.isdigit() or not 1 <= int(sel) <= len(devices):
                print("Invalid device")
                continue
            device_path, device_name = devices[int(sel) - 1]
            controls = get_control_list(device_path, stick_mapping)
            for i, (code, c) in enumerate(controls, 1):
                ctype = "button" if c["event_type"] == 1 else c.get("type", "")
                print(f"{i}. {c['name']} ({ctype}) code={code}")
            csel = input("Control #: ").strip()
            if not csel.isdigit() or not 1 <= int(csel) <= len(controls):
                print("Invalid control")
                continue
            control_code, control_info = controls[int(csel) - 1]
            model_mapping["channels"][channel] = {
                "device_path": device_path,
                "device_name": device_name,
                "control_code": control_code,
                "control_name": control_info["name"],
                "control_type": (
                    "button"
                    if control_info["event_type"] == 1
                    else control_info.get("type", "unipolar")
                ),
            }
            print(f"Channel {channel} mapped.")
        elif choice == "3":
            ch = input("Channel to remove: ").strip()
            if ch in model_mapping["channels"]:
                del model_mapping["channels"][ch]
                print("Removed.")
            else:
                print("Not mapped.")
        elif choice == "4":
            save_model_mapping(model_mapping, model_name)
            break
        elif choice == "5":
            print("Exiting without saving.")
            break


def main(_argv: list[str] | None = None):  # pragma: no cover
    try:
        create_mapping()
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":  # pragma: no cover
    main([])
