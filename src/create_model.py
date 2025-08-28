#!/usr/bin/env python3
import json
import os
from typing import Dict, Any, List, Tuple, Optional

MODELS_DIR = "models"


def load_stick_mapping(filename: str = "stick_mapping.json") -> Dict[str, Any]:
    """Load the stick mapping file."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found!")
        return {}


def get_available_models() -> List[str]:
    """Get a list of available model configurations."""
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
    return [f[:-5] for f in os.listdir(MODELS_DIR) if f.endswith(".json")]


def load_existing_model(model_name: str) -> Dict[str, Any]:
    """Load existing model mapping if it exists."""
    try:
        with open(os.path.join(MODELS_DIR, f"{model_name}.json"), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"name": model_name, "channels": {}}


def save_model_mapping(mapping: Dict[str, Any], model_name: str) -> None:
    """Save the model mapping to a file."""
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
    with open(os.path.join(MODELS_DIR, f"{model_name}.json"), "w") as f:
        json.dump(mapping, f, indent=2)
    # Also save as the active model
    with open("model_mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)


def get_device_list(stick_mapping: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Get a list of available devices."""
    return [(path, info["name"]) for path, info in stick_mapping.items()]


def get_control_list(
    device_path: str, stick_mapping: Dict[str, Any]
) -> List[Tuple[str, Dict[str, Any]]]:
    """Get a list of controls for a specific device."""
    device_info = stick_mapping[device_path]
    return [(code, control) for code, control in device_info["controls"].items()]


def print_available_controls(stick_mapping: Dict[str, Any]) -> None:
    """Print all available controls from the stick mapping."""
    print("\nAvailable controls by device:")

    for i, (device_path, device_info) in enumerate(stick_mapping.items(), 1):
        print(f"\nDevice {i}: {device_info['name']}")
        print(f"Path: {device_path}")
        print("-" * 70)
        print(f"{'#':<4} {'Control':<25} {'Type':<10} {'Code':<10}")
        print("-" * 70)

        for j, (code, control) in enumerate(device_info["controls"].items(), 1):
            control_type = "Button" if control["event_type"] == 1 else control["type"]
            print(f"{j:<4} {control['name']:<25} {control_type:<10} {code:<10}")


def print_current_model(model_mapping: Dict[str, Any]) -> None:
    """Print the current model mapping."""
    print(f"\nModel: {model_mapping.get('name', 'Unnamed')}")

    if not model_mapping["channels"]:
        print("\nNo channels mapped yet.")
        return

    print("\nChannel mapping:")
    print("-" * 100)
    print(f"{'Channel':<10} {'Device':<30} {'Path':<30} {'Control':<20}")
    print("-" * 100)

    for channel, mapping in sorted(model_mapping["channels"].items()):
        device_name = mapping.get("device_name", "Unknown")
        device_path = mapping.get("device_path", "Unknown")
        control_name = mapping.get("control_name", "Unknown")
        print(
            f"{channel:<10} {device_name[:30]:<30} {device_path[:30]:<30} {control_name:<20}"
        )


def select_or_create_model() -> Optional[str]:
    """Let the user select an existing model or create a new one."""
    while True:
        print("\nModel Selection")
        print("=" * 70)

        # Get available models
        models = get_available_models()
        if models:
            print("\nExisting models:")
            for i, model in enumerate(models, 1):
                print(f"{i}. {model}")
        else:
            print("\nNo existing models found.")

        print("\nOptions:")
        print("1. Create new model")
        if models:
            print("2. Load existing model")
        print("0. Exit")

        try:
            choice = input("\nEnter your choice: ").strip()

            if choice == "0":
                return None
            elif choice == "1":
                while True:
                    name = input("\nEnter name for new model: ").strip()
                    if not name:
                        print("Name cannot be empty!")
                        continue
                    if name in models:
                        print("Model with that name already exists!")
                        continue
                    if not name.replace("_", "").isalnum():
                        print(
                            "Name can only contain letters, numbers, and underscores!"
                        )
                        continue
                    return name
            elif choice == "2" and models:
                while True:
                    try:
                        idx = int(input("\nEnter model number: ").strip())
                        if 1 <= idx <= len(models):
                            return models[idx - 1]
                        print("Invalid model number!")
                    except ValueError:
                        print("Invalid input! Please enter a number.")
            else:
                print("Invalid choice!")
        except KeyboardInterrupt:
            return None


def create_mapping() -> None:
    """Main function to create a model mapping."""
    stick_mapping = load_stick_mapping()
    if not stick_mapping:
        return

    model_name = select_or_create_model()
    if not model_name:
        print("\nExiting...")
        return

    model_mapping = load_existing_model(model_name)

    while True:
        print("\nModel Mapping Configuration")
        print("=" * 70)
        print_current_model(model_mapping)
        print("\nOptions:")
        print("1. Show available controls")
        print("2. Map a channel")
        print("3. Remove a channel mapping")
        print("4. Save and exit")
        print("5. Exit without saving")

        try:
            choice = input("\nEnter your choice (1-5): ").strip()
        except KeyboardInterrupt:
            print("\nExiting without saving...")
            break

        if choice == "1":
            print_available_controls(stick_mapping)

        elif choice == "2":
            try:
                channel = input("\nEnter channel number (1-10): ").strip()
                if not channel.isdigit() or not 1 <= int(channel) <= 10:
                    print("Invalid channel number!")
                    continue

                # Get device list and show selection
                devices = get_device_list(stick_mapping)
                print("\nSelect device:")
                for i, (path, name) in enumerate(devices, 1):
                    print(f"{i}. {name}")
                    print(f"   Path: {path}")

                try:
                    device_choice = int(input("\nEnter device number: ").strip())
                    if not 1 <= device_choice <= len(devices):
                        print("Invalid device selection!")
                        continue
                except ValueError:
                    print("Invalid input! Please enter a number.")
                    continue

                device_path, device_name = devices[device_choice - 1]

                # Get control list for selected device and show selection
                controls = get_control_list(device_path, stick_mapping)
                print(f"\nSelect control for {device_name}:")
                for i, (_, control) in enumerate(controls, 1):
                    control_type = (
                        "Button" if control["event_type"] == 1 else control["type"]
                    )
                    print(f"{i}. {control['name']} ({control_type})")

                try:
                    control_choice = int(input("\nEnter control number: ").strip())
                    if not 1 <= control_choice <= len(controls):
                        print("Invalid control selection!")
                        continue
                except ValueError:
                    print("Invalid input! Please enter a number.")
                    continue

                control_code, control_info = controls[control_choice - 1]
                model_mapping["channels"][channel] = {
                    "device_path": device_path,
                    "device_name": device_name,
                    "control_code": control_code,
                    "control_name": control_info["name"],
                    "control_type": (
                        "button"
                        if control_info["event_type"] == 1
                        else control_info["type"]
                    ),
                }
                print(f"\nChannel {channel} mapped successfully!")

            except KeyboardInterrupt:
                print("\nMapping cancelled.")
                continue

        elif choice == "3":
            try:
                channel = input("\nEnter channel number to remove (1-10): ").strip()
                if channel in model_mapping["channels"]:
                    del model_mapping["channels"][channel]
                    print(f"Channel {channel} mapping removed.")
                else:
                    print("Channel not found in mapping!")
            except KeyboardInterrupt:
                print("\nRemoval cancelled.")
                continue

        elif choice == "4":
            save_model_mapping(model_mapping, model_name)
            print(f"\nModel '{model_name}' saved successfully!")
            break

        elif choice == "5":
            print("\nExiting without saving...")
            break


if __name__ == "__main__":
    try:
        create_mapping()
    except KeyboardInterrupt:
        print("\nExiting...")
