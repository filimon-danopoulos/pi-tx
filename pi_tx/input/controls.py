from __future__ import annotations
import threading, select, os
from queue import SimpleQueue
from datetime import datetime
from evdev import InputDevice, ecodes
from pathlib import Path
from ..infrastructure.file_cache import load_json


class InputController:
    """Reads mapped evdev devices and publishes normalized channel values via a queue.

    Only queue-based consumption is supported (no per-event callback registration).
    """

    def __init__(self, debug=False, mapping_file: str | None = None):
        if mapping_file is None:
            mapping_file = str(
                Path(__file__).parent / "mappings" / "stick_mapping.json"
            )
        self._stop_event = threading.Event()
        self._thread = None
        self._devices: list[InputDevice] = []
        self._debug = debug
        self._last_values: dict[str, dict[int, float]] = {}
        self._latch_states: dict[str, dict[int, int]] = {}
        self._last_key_raw: dict[str, dict[int, int]] = {}
        self._event_queue: SimpleQueue[tuple[int, float]] = SimpleQueue()
        self._channel_map: dict[str, dict[int, int]] = {}
        try:
            self._mappings = load_json(mapping_file, {})
        except Exception:
            print(f"Warning: Mapping file {mapping_file} not found")
            self._mappings = {}
        self._mapping_device_keys: list[str] = [
            k for k in self._mappings.keys() if k.startswith("/dev/input/")
        ]
        added = 0
        for k in list(self._mapping_device_keys):
            try:
                real = os.path.realpath(k)
            except Exception:
                continue
            if real and real != k and real not in self._mappings:
                self._mappings[real] = self._mappings[k]
                added += 1
        if added and self._debug:
            print(
                f"InputController: added {added} realpath alias mapping(s) for joystick devices"
            )

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self._stop_event.clear()
        # Discover devices before starting thread so we can prime synchronously
        self._devices = self._discover()
        if not self._devices:
            print("Input controller: no mapped input devices found.")
            return False
        # Prime once before launching event loop
        self.prime_values()
        # Launch event loop thread
        self._thread = threading.Thread(target=self._input_loop, daemon=True)
        self._thread.start()
        return True

    def prime_values(self):
        """Prime mapped ABS axes using current hardware state.

        Stores baseline in _last_values to avoid duplicate first events and enqueues
        initial values for mapped channels. Safe to call multiple times.
        """
        try:
            for dev in self._devices:
                mapped_codes = self._channel_map.get(dev.path, {})
                if not mapped_codes:
                    continue
                device_controls = self._mappings.get(dev.path, {}).get("controls", {})
                for code, ch_id in mapped_codes.items():
                    ctrl = device_controls.get(str(code))
                    if not ctrl or ctrl.get("event_type") != ecodes.EV_ABS:
                        continue
                    try:
                        abs_info = dev.absinfo(code)
                    except Exception:
                        continue
                    norm = self._normalize_value(
                        dev.path, ecodes.EV_ABS, code, abs_info.value
                    )
                    self._last_values.setdefault(dev.path, {})[code] = norm
                    if ch_id is not None:
                        self.enqueue_channel_value(ch_id, norm)
                    if self._debug:
                        print(f"Primed ABS dev={dev.path} code={code} norm={norm:.3f}")
        except Exception as e:
            if self._debug:
                print(f"Priming failed: {e}")

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

    def clear_values(self) -> None:
        """Clear cached last values (e.g., before reapplying a model)."""
        self._last_values.clear()

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
        # Normalize symlink (by-path/by-id) to its real event device so runtime dev.path matches
        real_path = None
        try:
            if device_path.startswith("/dev/input/"):
                import os

                real_path = os.path.realpath(device_path)
        except Exception:
            pass
        target_path = real_path or device_path
        if real_path and real_path != device_path:
            # optional: keep original key too, but main lookup uses real_path
            self._channel_map.setdefault(device_path, {})[event_code] = channel_id
        self._channel_map.setdefault(target_path, {})[event_code] = channel_id
        if self._debug:
            print(
                f"Registered channel {channel_id} code={event_code} for {device_path} (using {target_path})"
            )

    def _discover(self):
        if not self._mapping_device_keys:
            print("Input controller: no mapping device paths configured.")
            return []
        found: list[InputDevice] = []
        seen_real: set[str] = set()
        for configured in self._mapping_device_keys:
            try:
                real = os.path.realpath(configured)
                if real in seen_real:
                    continue
                dev = InputDevice(real)
                try:
                    dev.grab()
                except Exception as e:
                    if self._debug:
                        print(f"Non-exclusive access to {configured} -> {real}: {e}")
                found.append(dev)
                seen_real.add(real)
                if self._debug:
                    print(
                        f"Opened mapped device {dev.name} via {configured} (real {real})"
                    )
            except Exception as e:
                print(f"Mapping path {configured} unavailable: {e}")
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
            ctype = control.get("type", "button")
            if ctype in ("latching-button", "faux-switch"):
                # Initialize dict containers
                if device_path not in self._latch_states:
                    self._latch_states[device_path] = {}
                if device_path not in self._last_key_raw:
                    self._last_key_raw[device_path] = {}
                prev_raw = self._last_key_raw[device_path].get(event_code, 0)
                # Rising edge -> toggle latched state
                if prev_raw == 0 and value:
                    current = self._latch_states[device_path].get(event_code, 0)
                    self._latch_states[device_path][event_code] = 0 if current else 1
                # Update last raw
                self._last_key_raw[device_path][event_code] = value
                # Return latched state as float
                return float(self._latch_states[device_path].get(event_code, 0))
            # Regular momentary button -> pass through raw (0/1)
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
        # Devices already discovered & primed in start()
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
