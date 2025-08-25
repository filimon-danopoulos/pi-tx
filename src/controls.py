import threading, time, select
from datetime import datetime
from evdev import InputDevice, ecodes, list_devices


class InputController:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._devices = []

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

    def _is_joystick(self, dev: InputDevice) -> bool:
        caps = dev.capabilities()
        if ecodes.EV_ABS not in caps:
            return False

        # Must have joystick/gamepad buttons (BTN_JOYSTICK or BTN_GAMEPAD)
        btns = caps.get(ecodes.EV_KEY, [])
        has_joy_btns = any(code in ecodes.BTN for code in btns)
        if not has_joy_btns:
            return False

        # Filter out devices that look like touchpads
        name = (dev.name or "").lower()
        if "touchpad" in name or "synaptics" in name or "trackpad" in name:
            return False
        if "mouse" in name:
            return False
        if "keyboard" in name:
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
                    found.append(d)
                    print(f"Added {d.name} at {path}")
            except Exception as e:
                print(f"Failed to open {path}: {e}")
        return found

    def _ts(self):
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def _name_str(self, x):
        if isinstance(x, (tuple, list)):
            return str(x[0])
        return str(x)

    def _axis_name(self, code: int) -> str:
        name = ecodes.ABS.get(code)
        return self._name_str(name) if name else f"ABS_{code}"

    def _btn_name(self, code: int) -> str:
        name = ecodes.BTN.get(code)
        return self._name_str(name) if name else f"KEY_{code}"

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
                        if ev.type == ecodes.EV_SYN:
                            continue
                        name = self._name_str(dev.name)
                        path = dev.path
                        if ev.type == ecodes.EV_ABS:
                            axis = self._axis_name(ev.code)
                            val = ev.value
                            if axis.startswith("ABS_HAT"):
                                print(
                                    f"{self._ts()}  {name}({path})  HAT   {axis} -> {val}"
                                )
                            else:
                                print(
                                    f"{self._ts()}  {name}({path})  AXIS  {axis} -> {val}"
                                )
                        elif ev.type == ecodes.EV_KEY:
                            key = self._btn_name(ev.code)
                            state = "DOWN" if ev.value else "UP"
                            print(
                                f"{self._ts()}  {name}({path})  BTN   {key} -> {state}"
                            )
        finally:
            print("Input controller stopped")
