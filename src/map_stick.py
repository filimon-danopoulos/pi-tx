import json
import time
from evdev import InputDevice, ecodes, list_devices
from typing import Dict, Any, Optional, Tuple


def is_joystick(dev: InputDevice) -> bool:
    """Check if a device is a joystick/gamepad"""
    caps = dev.capabilities()
    if ecodes.EV_ABS not in caps:
        return False

    btns = caps.get(ecodes.EV_KEY, [])
    has_joy_btns = any(code in ecodes.BTN for code in btns)
    if not has_joy_btns:
        return False

    name = (dev.name or "").lower()
    non_joystick_keywords = [
        "touchpad",
        "synaptics",
        "trackpad",
        "mouse",
        "keyboard",
    ]
    return not any(x in name for x in non_joystick_keywords)


def monitor_inputs(
    dev: InputDevice, timeout: float = 5.0, active_timeout: float = 0.5
) -> Optional[Tuple[int, int, int, int]]:
    """Monitor device inputs and return the event with largest change.

    Args:
        dev: Input device to monitor
        timeout: Total time to wait for any input
        active_timeout: Time to wait after last movement before accepting input

    Returns:
        tuple: (event_type, event_code, min_value, max_value) of the most significant change
    """
    print("\nMove the control you want to map...")
    print("Movement will be detected after 0.5 seconds of no changes...")

    start_time = time.time()
    last_input_time = 0
    value_ranges = {}  # (type, code) -> (min_value, max_value)
    initial_values = {}  # (type, code) -> first_value

    while time.time() - start_time < timeout:
        current_time = time.time()

        # If we have input and it's been stable for active_timeout seconds, we're done
        if value_ranges and current_time - last_input_time > active_timeout:
            break

        try:
            for event in dev.read():
                if event.type not in [ecodes.EV_ABS, ecodes.EV_KEY]:
                    continue

                key = (event.type, event.code)
                last_input_time = current_time

                # Store initial value
                if key not in initial_values:
                    initial_values[key] = event.value
                    value_ranges[key] = [event.value, event.value]  # [min, max]
                    continue

                # Update min/max
                value_ranges[key][0] = min(value_ranges[key][0], event.value)
                value_ranges[key][1] = max(value_ranges[key][1], event.value)

        except BlockingIOError:
            time.sleep(0.1)

    if not value_ranges:
        return None

    # Find the input with the largest relative change
    max_change = 0
    most_significant = None

    for (ev_type, code), (min_val, max_val) in value_ranges.items():
        if ev_type == ecodes.EV_KEY:
            # For buttons, any change is significant
            if min_val != max_val:
                return (ev_type, code, min_val, max_val)

        elif ev_type == ecodes.EV_ABS:
            # For absolute axes, calculate change relative to the axis range
            abs_info = dev.absinfo(code)
            full_range = abs_info.max - abs_info.min
            if full_range == 0:
                continue

            observed_change = max_val - min_val
            relative_change = observed_change / full_range

            if relative_change > max_change:
                max_change = relative_change
                most_significant = (ev_type, code, min_val, max_val)

    return most_significant


def create_mapping(dev: InputDevice) -> Dict[str, Dict[str, Any]]:
    """Create a mapping by having the user identify each control"""
    device_info = {"name": dev.name, "controls": {}}

    print(f"\nDevice: {dev.name}")
    print(f"Path: {dev.path}")
    print("\nEntering continuous mapping mode...")
    print("Move each control you want to map.")
    print("Press Enter without a name to skip a control.")
    print("Wait 5 seconds without any control movement to finish mapping.\n")

    while True:
        result = monitor_inputs(dev)
        if not result:
            print("\nNo input detected for 5 seconds, finishing mapping...")
            break

        ev_type, code, min_val, max_val = result
        print("\nDetected control:")
        print(f"Type: {'ABS' if ev_type == ecodes.EV_ABS else 'KEY'}, Code: {code}")
        print(f"Range detected: {min_val} to {max_val}")

        # Check if this control is already mapped
        if code in device_info["controls"]:
            print(
                "This control is already mapped as:",
                device_info["controls"][code]["name"],
            )
            if input("Map it again? (y/N): ").lower() != "y":
                continue

        # Auto-detect control type for buttons, manual selection for axes
        if ev_type == ecodes.EV_KEY:
            control_type = "button"
        else:
            print("\nSelect axis type:")
            print("1. Unipolar (0 to max, like throttle)")
            print("2. Bipolar (-max to +max, like steering)")
            while True:
                type_choice = input("Enter choice (1-2): ").strip()
                if type_choice == "1":
                    control_type = "unipolar"
                    break
                elif type_choice == "2":
                    control_type = "bipolar"
                    break
                print("Invalid choice. Please enter 1 or 2.")

        name = input(
            "\nEnter a name for this control (or press Enter to skip): "
        ).strip()
        if not name:
            print("Skipping this control...")
            continue

        control_info = {
            "event_type": ev_type,
            "name": name,
            "type": control_type,
        }

        if ev_type == ecodes.EV_ABS:
            abs_info = dev.absinfo(code)
            control_info.update(
                {
                    "min": abs_info.min,
                    "max": abs_info.max,
                    "fuzz": abs_info.fuzz,
                    "flat": abs_info.flat,
                }
            )

        device_info["controls"][code] = control_info
        print("\nControl mapped successfully!")
        print("Move another control to map it, or wait 5 seconds to finish...")

        # After each mapping, show the current count
        print(f"\nMapped controls so far: {len(device_info['controls'])}")

    print("\nMapping finished!")

    # Show final mapping summary
    if device_info["controls"]:
        print("\nFinal mappings:")
        print("-" * 70)
        print(f"{'Code':<8} {'Name':<20} {'Type':<10} {'Range':<10} {'Input Type':<10}")
        print("-" * 70)

        for code, control in device_info["controls"].items():
            if control["type"] in ["unipolar", "bipolar"] and "min" in control:
                range_info = f"{control['min']} to {control['max']}"
            else:
                range_info = "0 or 1"

            input_type = "Axis" if control["event_type"] == ecodes.EV_ABS else "Button"
            print(
                f"{code:<8} {control['name']:<20} {control['type']:<10} {range_info:<10} {input_type:<10}"
            )

    return {dev.path: device_info}


def load_existing_mapping(filename: str) -> Dict[str, Any]:
    """Load an existing mapping file if it exists"""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_mapping(new_mapping: Dict[str, Any], filename: str) -> None:
    """Save mapping information to a JSON file, merging with existing mappings"""
    # Load existing mappings if any
    all_mappings = load_existing_mapping(filename)

    # Update with new mapping
    all_mappings.update(new_mapping)

    # Save back to file
    with open(filename, "w") as f:
        json.dump(all_mappings, f, indent=2)


def show_device_status(
    devices: list[InputDevice], existing_mappings: Dict[str, Any]
) -> None:
    """Show status of available devices and their mapping status"""
    print("\nAvailable devices:")
    print("-" * 70)
    print(f"{'#':<3} {'Name':<30} {'Path':<20} {'Status':<15}")
    print("-" * 70)

    for i, dev in enumerate(devices, 1):
        status = "Mapped" if dev.path in existing_mappings else "Not mapped"
        if status == "Mapped":
            control_count = len(existing_mappings[dev.path]["controls"])
            status = f"Mapped ({control_count})"
        print(f"{i:<3} {dev.name[:30]:<30} {dev.path[:20]:<20} {status:<15}")
    print("-" * 70)


def main():
    print("Scanning for joysticks...")

    # Find all potential devices
    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            if is_joystick(dev):
                devices.append(dev)
        except Exception as e:
            print(f"Failed to open {path}: {e}")

    if not devices:
        print("No joysticks found!")
        return

    # Load existing mappings
    filename = "stick_mapping.json"
    existing_mappings = load_existing_mapping(filename)

    while True:
        show_device_status(devices, existing_mappings)

        print("\nOptions:")
        print("1. Map/Remap a device")
        print("2. Review existing mappings")
        print("3. Exit")

        choice = input("\nEnter your choice (1-3): ").strip()

        if choice == "1":
            # Select device to map
            print("\nSelect device to map:")
            for i, dev in enumerate(devices, 1):
                status = "Mapped" if dev.path in existing_mappings else "Not mapped"
                if status == "Mapped":
                    control_count = len(existing_mappings[dev.path]["controls"])
                    status = f"Mapped ({control_count} controls)"
                print(f"{i}. {dev.name} - {status}")

            device_choice = input("\nChoose device (enter number): ").strip()
            try:
                device = devices[int(device_choice) - 1]
            except (ValueError, IndexError):
                print("Invalid choice!")
                continue

            try:
                device.grab()  # Grab the device for exclusive access
                mapping = create_mapping(device)

                if mapping[device.path]["controls"]:  # Only save if we mapped something
                    save_mapping(mapping, filename)
                    existing_mappings = load_existing_mapping(
                        filename
                    )  # Reload mappings
                    print(f"\nMapping saved to {filename}")
                else:
                    print("\nNo controls were mapped.")

            finally:
                device.ungrab()  # Always release the device

        elif choice == "2":
            # Show existing mappings for each device
            if not existing_mappings:
                print("\nNo mappings found.")
                continue

            print("\nExisting mappings:")
            print("=" * 70)

            for path, info in existing_mappings.items():
                print(f"\nDevice: {info['name']}")
                print(f"Path: {path}")
                print("-" * 70)
                print(
                    f"{'Code':<8} {'Name':<20} {'Type':<10} {'Range':<10} {'Input Type':<10}"
                )
                print("-" * 70)

                for code, control in info["controls"].items():
                    if control["type"] in ["unipolar", "bipolar"] and "min" in control:
                        range_info = f"{control['min']} to {control['max']}"
                    else:
                        range_info = "0 or 1"

                    input_type = (
                        "Axis" if control["event_type"] == ecodes.EV_ABS else "Button"
                    )
                    print(
                        f"{code:<8} {control['name']:<20} {control['type']:<10} {range_info:<10} {input_type:<10}"
                    )

            input("\nPress Enter to continue...")

        elif choice == "3":
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
