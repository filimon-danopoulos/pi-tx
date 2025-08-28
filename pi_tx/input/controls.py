from __future__ import annotations
import threading, time, select, json
from queue import SimpleQueue
from datetime import datetime
from evdev import InputDevice, ecodes, list_devices
from pathlib import Path


class InputController:
    def __init__(self, debug=False, mapping_file: str | None = None):
        if mapping_file is None:
            mapping_file = str(
                Path(__file__).parent / "mappings" / "stick_mapping.json"
            )
        self._stop_event = threading.Event()
        self._thread = None
        self._devices: list[InputDevice] = []
        self._callbacks: dict[str, dict[int, callable]] = {}
        self._debug = debug
        self._last_values: dict[str, dict[int, float]] = {}
        self._event_queue: SimpleQueue[tuple[int, float]] = SimpleQueue()
        self._callback_mode = True
        self._channel_map: dict[str, dict[int, int]] = {}
        try:
            with open(mapping_file, "r") as f:
                self._mappings = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Mapping file {mapping_file} not found")
            self._mappings = {}

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
        if device_path not in self._callbacks:
            self._callbacks[device_path] = {}
        self._callbacks[device_path][event_code] = callback

    def clear_callbacks(self) -> None:
        self._callbacks.clear()
        self._last_values.clear()

    # Queue mode
    def enable_queue_mode(self):
        self._callback_mode = False

    def enqueue_channel_value(self, channel_id: int, value: float):
        self._event_queue.put((channel_id, value))

    def pop_events(self, max_batch: int = 128):
        events = []
        for _ in range(max_batch):
            try:
                events.append(self._event_queue.get_nowait())
            except Exception:
                break
        return events

    def register_channel_mapping(
        self, device_path: str, event_code: int, channel_id: int
    ):
        self._channel_map.setdefault(device_path, {})[event_code] = channel_id

    def _is_joystick(self, dev: InputDevice) -> bool:
        caps = dev.capabilities()
        if ecodes.EV_ABS not in caps:
            return False
        btns = caps.get(ecodes.EV_KEY, [])
        has_joy_btns = any(code in ecodes.BTN for code in btns)
        if not has_joy_btns:
            return False
        name = (dev.name or "").lower()
        for k in ["touchpad", "synaptics", "trackpad", "mouse", "keyboard"]:
            if k in name:
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
                    if d.path in self._mappings:
                        found.append(d)
                        print(f"Added {d.name} at {path} (mapped device)")
                    else:
                        print(f"Skipping {d.name} at {path} (no mapping)")
                        d.ungrab()
            except Exception as e:
                print(f"Failed to open {path}: {e}")
        return found

    def _normalize_value(
        self, device_path: str, event_type: int, event_code: int, value: int
    ) -> float:
        device_mapping = self._mappings.get(device_path, {}).get("controls", {})
        code_str = str(event_code)
        if code_str not in device_mapping:
            return 0.0
        control = device_mapping[code_str]
        if control["event_type"] != event_type:
            return 0.0
        if event_type == ecodes.EV_KEY:
            return float(value)
        if event_type == ecodes.EV_ABS:
            min_val, max_val = control["min"], control["max"]
            axis_type = control.get("type", "bipolar")
            if axis_type == "unipolar":
                normalized = (value - min_val) / (max_val - min_val)
                normalized = max(0.0, min(1.0, normalized))
            else:
                normalized = (2.0 * (value - min_val) / (max_val - min_val)) - 1.0
                normalized = max(-1.0, min(1.0, normalized))
            if abs(normalized) < 0.05:
                return 0.0
            return normalized
        return 0.0

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
                        if ev.type in (ecodes.EV_SYN, ecodes.EV_MSC):
                            continue
                        norm = self._normalize_value(
                            dev.path, ev.type, ev.code, ev.value
                        )
                        if dev.path not in self._last_values:
                            self._last_values[dev.path] = {}
                        last = self._last_values[dev.path].get(ev.code)
                        if last != norm:
                            self._last_values[dev.path][ev.code] = norm
                            if self._callback_mode:
                                cb = self._callbacks.get(dev.path, {}).get(ev.code)
                                if cb:
                                    try:
                                        cb(norm)
                                    except Exception as e:
                                        print(
                                            f"Error in callback {dev.path} {ev.code}: {e}"
                                        )
                            else:
                                ch_id = self._channel_map.get(dev.path, {}).get(ev.code)
                                if ch_id is not None:
                                    self.enqueue_channel_value(ch_id, norm)
                        if self._debug:
                            status = "changed" if last != norm else "filtered"
                            print(
                                f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} dev={dev.path} code={ev.code} raw={ev.value} norm={norm:.3f} {status}"
                            )
        finally:
            print("Input controller stopped")
