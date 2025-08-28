"""Interactive joystick mapping tool.

Invoke via:
  python -m pi_tx.tools map-stick
"""

from __future__ import annotations
import json, time
from typing import Dict, Any, Optional, Tuple
from evdev import InputDevice, ecodes, list_devices
from pi_tx.config.settings import STICK_MAPPING_FILE, MAPPINGS_DIR


def is_joystick(dev: InputDevice) -> bool:
    caps = dev.capabilities()
    if ecodes.EV_ABS not in caps:
        return False
    btns = caps.get(ecodes.EV_KEY, [])
    if not any(code in ecodes.BTN for code in btns):
        return False
    name = (dev.name or "").lower()
    for k in ["touchpad", "synaptics", "trackpad", "mouse", "keyboard"]:
        if k in name:
            return False
    return True


def monitor_inputs(
    dev: InputDevice, timeout: float = 5.0, active_timeout: float = 0.5
) -> Optional[Tuple[int, int, int, int]]:
    print("\nMove the control you want to map... (stable 0.5s to capture)")
    start = time.time()
    last_input = 0
    value_ranges: Dict[Tuple[int, int], list[int]] = {}
    initial: Dict[Tuple[int, int], int] = {}
    while time.time() - start < timeout:
        now = time.time()
        if value_ranges and now - last_input > active_timeout:
            break
        try:
            for ev in dev.read():
                if ev.type not in (ecodes.EV_ABS, ecodes.EV_KEY):
                    continue
                key = (ev.type, ev.code)
                last_input = now
                if key not in initial:
                    initial[key] = ev.value
                    value_ranges[key] = [ev.value, ev.value]
                    continue
                rng = value_ranges[key]
                if ev.value < rng[0]:
                    rng[0] = ev.value
                if ev.value > rng[1]:
                    rng[1] = ev.value
        except BlockingIOError:
            time.sleep(0.05)
    if not value_ranges:
        return None
    max_change = 0.0
    selected = None
    for (ev_type, code), (vmin, vmax) in value_ranges.items():
        if ev_type == ecodes.EV_KEY:
            if vmin != vmax:
                return (ev_type, code, vmin, vmax)
        else:
            abs_info = dev.absinfo(code)
            full = abs_info.max - abs_info.min
            if full <= 0:
                continue
            rel = (vmax - vmin) / full
            if rel > max_change:
                max_change = rel
                selected = (ev_type, code, vmin, vmax)
    return selected


def load_existing_mapping() -> Dict[str, Any]:
    try:
        with open(STICK_MAPPING_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_mapping(mapping: Dict[str, Any]):
    MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STICK_MAPPING_FILE, "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"Saved mapping to {STICK_MAPPING_FILE}")


def show_device_status(devices, existing):
    print("\nAvailable devices:\n" + "-" * 70)
    print(f"{'#':<3} {'Name':<30} {'Path':<22} {'Status':<12}")
    print("-" * 70)
    for i, d in enumerate(devices, 1):
        status = "Mapped" if d.path in existing else "Not mapped"
        if status == "Mapped":
            status += f" ({len(existing[d.path]['controls'])})"
        print(f"{i:<3} {d.name[:30]:<30} {d.path[:22]:<22} {status:<12}")


def create_mapping(dev: InputDevice):
    device_info = {"name": dev.name, "controls": {}}
    print(f"\nMapping device: {dev.name} ({dev.path})")
    print("Move controls; wait 5s of inactivity to finish. Enter to skip a control.")
    while True:
        result = monitor_inputs(dev)
        if not result:
            print("Finished mapping session.")
            break
        ev_type, code, vmin, vmax = result
        print(
            f"Detected {'ABS' if ev_type==ecodes.EV_ABS else 'KEY'} code={code} range={vmin}->{vmax}"
        )
        if code in device_info["controls"]:
            print("Already mapped as", device_info["controls"][code]["name"])
            if input("Remap? (y/N): ").lower() != "y":
                continue
        if ev_type == ecodes.EV_KEY:
            ctype = "button"
        else:
            print("Axis type: 1) unipolar  2) bipolar")
            while True:
                sel = input("Choice (1-2): ").strip()
                if sel == "1":
                    ctype = "unipolar"
                    break
                if sel == "2":
                    ctype = "bipolar"
                    break
                print("Invalid")
        name = input("Name (blank to skip): ").strip()
        if not name:
            print("Skipped.")
            continue
        info = {"event_type": ev_type, "name": name, "type": ctype}
        if ev_type == ecodes.EV_ABS:
            abs_info = dev.absinfo(code)
            info.update(
                {
                    "min": abs_info.min,
                    "max": abs_info.max,
                    "fuzz": abs_info.fuzz,
                    "flat": abs_info.flat,
                }
            )
        device_info["controls"][code] = info
        print(f"Mapped {name} (code {code})")
    return {dev.path: device_info}


def main(_argv: list[str] | None = None):  # pragma: no cover
    print("Scanning for joysticks...")
    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
            if is_joystick(dev):
                devices.append(dev)
        except Exception as e:
            print(f"Failed to open {path}: {e}")
    if not devices:
        print("No joysticks found")
        return 1
    existing = load_existing_mapping()
    while True:
        show_device_status(devices, existing)
        print("\nOptions:\n1. Map/Remap a device\n2. Review mappings\n3. Exit")
        choice = input("Choice (1-3): ").strip()
        if choice == "1":
            sel = input("Device #: ").strip()
            if not sel.isdigit() or not 1 <= int(sel) <= len(devices):
                print("Invalid")
                continue
            dev = devices[int(sel) - 1]
            try:
                dev.grab()
                new_map = create_mapping(dev)
                if new_map[dev.path]["controls"]:
                    existing.update(new_map)
                    save_mapping(existing)
                else:
                    print("No controls mapped.")
            finally:
                try:
                    dev.ungrab()
                except Exception:
                    pass
        elif choice == "2":
            if not existing:
                print("No mappings yet.")
                continue
            for path, info in existing.items():
                print(f"\nDevice: {info['name']} ({path})")
                for code, ctrl in info["controls"].items():
                    rng = (
                        f"{ctrl.get('min','?')}->{ctrl.get('max','?')}"
                        if ctrl["event_type"] == ecodes.EV_ABS
                        else "0/1"
                    )
                    print(
                        f" code={code:<4} name={ctrl['name']:<18} type={ctrl['type']:<8} range={rng}"
                    )
            input("\nEnter to continue...")
        elif choice == "3":
            return 0
        else:
            print("Invalid")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main([]))
