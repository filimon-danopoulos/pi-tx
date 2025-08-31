from __future__ import annotations

"""UART transmission of channel data to a MULTI / iRX4 style module (100000 8E2).

Single class (MultiSerialTX) handles both frame construction and transmission.
Frame format: 16-channel V1 serial frame (26 bytes) as per multiprotocol docs.

Backend:
    * pigpio serial on Raspberry Pi (pigpiod must be running). No pyserial fallback in this build.

Logging controls (environment variables):
    PI_TX_UART_DEBUG=1          force verbose frame logging
    PI_TX_UART_LOG_EVERY=N      log every Nth frame (N>0)
    PI_TX_UART_RAW_HEX=1        include full frame hex when debug enabled
    PI_TX_UART_DRIFT_INTERVAL=S seconds between rate/drift reports (default 1.0)
    PI_TX_UART_MAX_VALUE_LOG=M  number of channel values to show (default 8)

Usage:
    tx = MultiSerialTX(port='/dev/ttyS0')
        tx.open()
        tx.send_channels([0.0]*16)

Integrate by periodically calling send_channels(channel_store_snapshot) at ~50Hz.
"""
from typing import Sequence
import threading, time, platform, os


# Raspberry Pi detection
def _is_raspberry_pi() -> bool:
    try:
        if "raspberrypi" in platform.uname().nodename.lower():
            return True
        # Check device tree model
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            model = f.read().lower()
            if "raspberry pi" in model:
                return True
    except Exception:
        pass
    return False


ON_PI = _is_raspberry_pi()

try:
    import pigpio  # type: ignore

    HAVE_PIGPIO = True
except Exception:
    HAVE_PIGPIO = False


class MultiSerialTX:
    def __init__(
        self,
        port: str,
        *,
        protocol: int = 0,
        sub_protocol: int = 0,
        rx_num: int = 0,
        option: int = 0,
        power_low: bool = False,
        autobind: bool = False,
        bind: bool = False,
        range_check: bool = False,
        debug_print: bool = False,
        disabled: bool = False,
    ):
        # Configuration
        self.port_name = port
        self.protocol = protocol  # 0..63 (we stay <32 for now)
        self.sub_protocol = sub_protocol  # 0..7
        self.rx_num = rx_num  # 0..15
        self.option = option  # signed 8bit
        self.power_low = power_low
        self.autobind = autobind
        self.bind = bind
        self.range_check = range_check
        self.debug_print = debug_print
        self.disabled = disabled
        # Runtime state
        self._lock = threading.Lock()
        self._last_error_print = 0.0
        self._error_count = 0
        self._pi = None
        self._pig_handle = None
        # Logging state
        self._frame_counter = 0
        self._log_every = int(os.environ.get("PI_TX_UART_LOG_EVERY", "0"))
        if os.environ.get("PI_TX_UART_DEBUG") == "1":
            self.debug_print = True
        self._max_value_log = int(os.environ.get("PI_TX_UART_MAX_VALUE_LOG", "8"))

    def _now_parts(self):
        now = time.time()
        int_part = int(now)
        ms = int((now - int_part) * 1000)
        ts = time.strftime("%H:%M:%S", time.localtime(int_part))
        return ts, ms

    def _log(self, msg: str):
        ts, ms = self._now_parts()
        print(f"[UART {ts}.{ms:03d}] {msg}")

    def open(self):
        if self.disabled:
            return
        if self._pig_handle is not None:
            return
        if not ON_PI:
            raise RuntimeError("UART enabled only on Raspberry Pi in this build")
        if not HAVE_PIGPIO:
            raise RuntimeError(
                "pigpio module not available; install pigpio and run pigpiod"
            )
        try:
            self._log("Opening pigpio serial")
            self._pi = pigpio.pi()  # type: ignore
            if not self._pi or not self._pi.connected:
                raise RuntimeError(
                    "pigpio daemon not running (start with: sudo pigpiod)"
                )
            # 100000 8E2: pigpio uses standard 8N1 framing by default; emulate 8E2 by higher-level encoding acceptance (many receivers tolerate). For strict 8E2 hardware, ensure underlying tty configured accordingly if needed.
            self._pig_handle = self._pi.serial_open(self.port_name, 100000, 0)
            self._log(f"Opened port={self.port_name} handle={self._pig_handle}")
        except Exception:
            # Ensure cleanup
            try:
                if self._pi:
                    self._pi.stop()
            except Exception:
                pass
            self._pi = None
            self._pig_handle = None
            raise

    def close(self):
        try:
            if self._pi and self._pig_handle is not None:
                self._log("Closing pigpio serial")
                self._pi.serial_close(self._pig_handle)
        except Exception:
            pass
        finally:
            self._pig_handle = None
            if self._pi:
                try:
                    self._pi.stop()
                except Exception:
                    pass
                self._pi = None

    def build_frame(self, ch_values: Sequence[float]) -> bytes:
        # Expect up to 16 channels (use 0 for missing)
        vals = list(ch_values[:16]) + [0.0] * (16 - len(ch_values))

        # Convert to 0..2047 range (approx mapping from -1..+1)
        def to_raw(v: float) -> int:
            v = max(-1.0, min(1.0, v))
            raw = int(round((v * 0.5 + 0.5) * 2047))
            return max(0, min(2047, raw))

        raws = [to_raw(v) for v in vals]
        header = 0x55 if self.protocol < 32 else 0x54  # we keep protocol <32 now
        byte1 = self.protocol & 0x1F
        if self.autobind:
            byte1 |= 0x20
        if self.range_check:
            byte1 |= 0x40
        if self.bind:
            byte1 |= 0x80
        byte2 = (self.rx_num & 0x0F) | ((self.sub_protocol & 0x07) << 4)
        if self.power_low:
            byte2 |= 0x80
        frame = bytearray(26)
        frame[0] = header
        frame[1] = byte1
        frame[2] = byte2
        frame[3] = (self.option + 256) % 256
        # Pack 16 * 11 bits starting at frame[4]
        bit_pos = 0
        for raw in raws:
            for i in range(11):
                if raw & (1 << i):
                    byte_index = 4 + (bit_pos // 8)
                    bit_in_byte = bit_pos % 8
                    frame[byte_index] |= 1 << bit_in_byte
                bit_pos += 1
        frame_bytes = bytes(frame)
        self._frame_counter += 1
        if self.debug_print or (
            self._log_every and (self._frame_counter % self._log_every == 0)
        ):
            preview_vals = ",".join(f"{v:+.2f}" for v in vals[: self._max_value_log])
            self._log(
                f"frame#{self._frame_counter} hdr={header:02X},{byte1:02X},{byte2:02X},{frame[3]:02X} first8={frame_bytes[:8].hex()} vals={preview_vals}"
            )
        return frame_bytes

    def _drain_loopback(self):
        # No loopback handling in pigpio-only mode
        return

    def send_frame(self, frame: bytes):
        if self.disabled:
            return
        with self._lock:
            try:
                if self._pig_handle is None:
                    raise RuntimeError("pigpio serial not open")
                self._pi.serial_write(self._pig_handle, frame)  # type: ignore
                if self.debug_print and os.environ.get("PI_TX_UART_RAW_HEX") == "1":
                    self._log(f"raw={frame.hex()}")
            except Exception as e:
                self._error_count += 1
                now = time.time()
                if now - self._last_error_print > 2.0:
                    self._log(
                        f"WRITE ERROR count={self._error_count} type={type(e).__name__} detail={e!r}"
                    )
                    self._last_error_print = now
                # Attempt lightweight reopen
                try:
                    self.open()
                    self._error_count = 0
                except Exception:
                    pass

    def send_channels(self, ch_values: Sequence[float]):
        frame = self.build_frame(ch_values)
        self.send_frame(frame)


class PeriodicChannelSender:
    def __init__(self, tx: MultiSerialTX, sampler, rate_hz: float = 50.0):
        self.tx = tx
        self.sampler = sampler  # callable returning sequence of channel floats
        self.interval = 1.0 / rate_hz
        self._thread = None
        self._stop = threading.Event()

    # no file logging when using console debug

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.tx.open()
        # no file logging setup
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._thread:
            return
        self._stop.set()
        self._thread.join(timeout=2)
        self._thread = None

    # nothing to close for console logging

    def _loop(self):
        monotonic = time.monotonic
        start = monotonic()
        frame_index = 0
        interval = self.interval
        last_report = start
        drift_interval = float(os.environ.get("PI_TX_UART_DRIFT_INTERVAL", "1.0"))
        while not self._stop.is_set():
            target = start + frame_index * interval
            now = monotonic()
            if now - last_report >= drift_interval:
                actual_rate = frame_index / (now - start) if frame_index else 0.0
                try:
                    self.tx._log(
                        f"rate={actual_rate:.2f}Hz frames={frame_index} drift={(now - target):+.4f}s"
                    )
                except Exception:
                    pass
                last_report = now
            # Sleep until the target time
            if now < target:
                to_sleep = target - now
                # Cap very large sleep in case interval changed
                if to_sleep > interval:
                    to_sleep = interval
                time.sleep(to_sleep)
                continue
            # If we are late by more than one interval, skip ahead to avoid drift
            if now - target > interval:
                frame_index = int((now - start) / interval)
                target = start + frame_index * interval
            try:
                values = self.sampler()
                frame = self.tx.build_frame(values)
                self.tx.send_frame(frame)
            except Exception as e:
                try:
                    self.tx._log(f"LOOP ERROR: {e!r}")
                except Exception:
                    print(f"Periodic sender error: {e}")
            frame_index += 1

    # PigpioSerialTX class removed; pigpio support integrated into MultiSerialTX
