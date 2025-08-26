import threading, time, select
from datetime import datetime
from evdev import InputDevice, ecodes, list_devices


class InputController:
    def __init__(self, debug=False):
        self._stop_event = threading.Event()
        self._thread = None
        self._devices = []
        self._callbacks = {}
        self._debug = debug
        self._device_info = {}
        self._last_values = {}

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._input_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        if not self._thread:
            return False
        self._stop_event.set()
        self._thread.join(timeout=2.0)
        for d in self._devices:
            try:
                d.ungrab()
                d.close()
            except Exception:
                pass
        self._devices.clear()
        return True

    def register_callback(self, device_path: str, event_code: int, callback) -> None:
        """Register a callback for a specific device and event code.

        Args:
            device_path: The path to the input device (e.g., '/dev/input/event0')
            event_code: The event code to listen for
            callback: Function to call when the event occurs. Will be called with (device_path, event)
        """
        if device_path not in self._callbacks:
            self._callbacks[device_path] = {}
        self._callbacks[device_path][event_code] = callback

    def clear_callbacks(self) -> None:
        """Clear all registered callbacks and last values.
        This resets the controller to its initial state, removing all callback registrations
        and forgetting all last known values.
        """
        self._callbacks.clear()
        self._last_values.clear()

    def _is_joystick(self, dev: InputDevice) -> bool:
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
        if any(x in name for x in non_joystick_keywords):
            return False

        return True

    def _discover(self):
        found = []
        for path in list_devices():
            try:
                d = InputDevice(path)
                if self._is_joystick(d):
                    try:
                        d.grab()
                    except Exception as e:
                        print(f"Could not grab {path} ({d.name}): {e}")
                        continue

                    abs_info = {}
                    if ecodes.EV_ABS in d.capabilities():
                        for code, info in d.capabilities()[ecodes.EV_ABS]:
                            abs_info[code] = {
                                "min": info.min,
                                "max": info.max,
                                "fuzz": info.fuzz,
                                "flat": info.flat,
                            }
                    self._device_info[d.path] = {"abs_info": abs_info}

                    found.append(d)
                    print(f"Added {d.name} at {path}")
            except Exception as e:
                print(f"Failed to open {path}: {e}")
        return found

    def _normalize_value(
        self, device_path: str, event_type: int, event_code: int, value: int
    ) -> float:
        """Normalize input values to range [-1, 1] for axes and [0, 1] for buttons."""
        if event_type == ecodes.EV_KEY:
            # Button values are 0 or 1
            return float(value)

        if event_type == ecodes.EV_ABS:
            device_info = self._device_info.get(device_path, {})
            abs_info = device_info.get("abs_info", {}).get(event_code)

            if abs_info:
                min_val = abs_info["min"]
                max_val = abs_info["max"]

                # First normalize to [-1, 1]
                normalized = (2.0 * (value - min_val) / (max_val - min_val)) - 1.0
                normalized = max(-1.0, min(1.0, normalized))

                # Apply percentage-based deadzone
                deadzone = 0.05
                if abs(normalized) < deadzone:
                    return 0.0

                return normalized

        return 0

    # ---- main loop ----
    def _input_loop(self):
        self._devices = self._discover()
        if not self._devices:
            print("Input controller: no joystick-like devices found.")
            return

        try:
            while not self._stop_event.is_set():
                r, _, _ = select.select([d.fd for d in self._devices], [], [], 0.25)
                if not r:
                    continue
                for fd in r:
                    dev = next((d for d in self._devices if d.fd == fd), None)
                    if not dev:
                        continue
                    for ev in dev.read():
                        if ev.type == ecodes.EV_SYN or ev.type == ecodes.EV_MSC:
                            continue

                        # Normalize the value
                        normalized_value = self._normalize_value(
                            dev.path, ev.type, ev.code, ev.value
                        )

                        # Get last value for this device/event combination
                        if dev.path not in self._last_values:
                            self._last_values[dev.path] = {}
                        last_value = self._last_values[dev.path].get(ev.code)

                        # Check if value has changed
                        if last_value != normalized_value:
                            # Update stored value
                            self._last_values[dev.path][ev.code] = normalized_value

                            # Call registered callbacks for this device and event
                            device_callbacks = self._callbacks.get(dev.path, {})
                            callback = device_callbacks.get(ev.code)
                            if callback:
                                try:
                                    callback(normalized_value)
                                except Exception as e:
                                    print(
                                        f"Error in callback for {dev.path}, event {ev.code}: {e}"
                                    )

                        # Print debug info
                        if self._debug:
                            status = (
                                "changed"
                                if last_value != normalized_value
                                else "filtered"
                            )
                            print(
                                f"{datetime.now().strftime("%H:%M:%S.%f")[:-3]}  dev={dev.path}  type={ev.type}  code={ev.code}  "
                                f"raw={ev.value}  normalized={normalized_value:.3f}  {status}"
                            )
        finally:
            print("Input controller stopped")
